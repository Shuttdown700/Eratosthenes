import os
import pathlib
import warnings
import difflib
import subprocess
import numpy as np
import nltk
import torch
import librosa
import whisper
import lyricsgenius
from demucs.pretrained import get_model
from demucs.apply import apply_model
from demucs.audio import AudioFile
from pydub import AudioSegment
import soundfile as sf
from mutagen.mp3 import MP3
from mutagen.id3 import ID3
from colorama import init, Fore, Style

# -------------------------------
# Setup colors
# -------------------------------
init(autoreset=True)
RED = Fore.RED
YELLOW = Fore.YELLOW
GREEN = Fore.GREEN
BLUE = Fore.BLUE
MAGENTA = Fore.MAGENTA
RESET = Style.RESET_ALL
BRIGHT = Style.BRIGHT

# -------------------------------
# Suppress FP16 warning on CPU
# -------------------------------
warnings.filterwarnings("ignore", message="FP16 is not supported on CPU; using FP32 instead")

# -------------------------------
# Download NLTK punkt_tab if not present
# -------------------------------
try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    print(f"{YELLOW}Downloading NLTK punkt_tab resource...{RESET}")
    nltk.download('punkt_tab')

# -------------------------------
# FFmpeg setup
# -------------------------------
BASE_DIR = pathlib.Path(__file__).resolve().parent
FFMPEG_PATH = (BASE_DIR / "../bin/ffmpeg.exe").resolve()
os.environ["PATH"] += os.pathsep + str(FFMPEG_PATH.parent)
os.environ["FFMPEG_BINARY"] = str(FFMPEG_PATH)
print(f"{GREEN}Using ffmpeg at: {FFMPEG_PATH}{RESET}")

# -------------------------------
# Helper functions
# -------------------------------
def format_timestamp(seconds: float) -> str:
    m, s = divmod(seconds, 60)
    return f"[{int(m):02d}:{s:05.2f}]"

def normalize(text: str) -> str:
    return "".join(c.lower() for c in text if c.isalnum() or c.isspace()).strip()

def is_repetitive(text: str) -> bool:
    words = text.lower().split()
    if not words:
        return False
    unique_words = set(words)
    if len(unique_words) <= 2 and all(len(word) <= 4 for word in words):
        return True
    if len(words) >= 2 and all(word == words[0] for word in words):
        return True
    return False

def convert_to_wav(input_path: str, output_path: str) -> None:
    subprocess.run([str(FFMPEG_PATH), "-i", input_path, "-ar", "44100", "-ac", "2", output_path], check=True)

def preprocess_vocals(vocals_path: str, output_path: str) -> None:
    audio = AudioSegment.from_wav(vocals_path)
    audio = audio.high_pass_filter(200).compress_dynamic_range(threshold=-20.0)
    audio = audio.apply_gain(-audio.max_dBFS)  # Normalize to 0 dBFS
    audio.export(output_path, format="wav")

def isolate_vocals_demucs(mp3_path: str, output_dir: str) -> str:
    print(f"Running Demucs vocal separation for {mp3_path}")
    audio = AudioFile(mp3_path).read(streams=0, samplerate=44100)
    print(f"Input audio shape: {audio.shape}")
    sr = 44100

    if len(audio.shape) == 2:
        audio = audio.unsqueeze(0)
    else:
        raise ValueError(f"Unexpected audio shape: {audio.shape}")
    print(f"Reshaped audio for Demucs: {audio.shape}")

    model_demucs = get_model("mdx_extra")
    model_demucs.to(device)
    model_demucs.eval()

    with torch.no_grad():
        sources = apply_model(model_demucs, audio, device=device)
    print(f"Demucs output shape: {sources.shape}")

    if len(sources.shape) == 4:
        vocals = sources[0, 3].cpu().numpy()
    elif len(sources.shape) == 3:
        vocals = sources[3].cpu().numpy()
    elif len(sources.shape) == 2:
        vocals = sources[3].cpu().numpy()
        vocals = vocals[:, None]
    else:
        raise ValueError(f"Unexpected Demucs output shape: {sources.shape}")

    stem_names = ["drums", "bass", "other", "vocals"]
    print(f"{BLUE}Stem analysis:{RESET}")
    for i, name in enumerate(stem_names):
        if len(sources.shape) == 4:
            stem_data = sources[0, i].cpu().numpy()
        else:
            stem_data = sources[i].cpu().numpy()
        max_val = np.max(np.abs(stem_data))
        print(f"  {name}: Max value = {max_val:.4f}")

    print(f"Vocals shape: {vocals.shape}, Max value: {np.max(np.abs(vocals))}")

    vocals = vocals * 3.0
    if np.max(np.abs(vocals)) > 0:
        vocals = vocals / np.max(np.abs(vocals))
    else:
        print(f"{RED}Warning: Vocals tensor is all zeros, saving original audio instead{RESET}")
        vocals = audio[0].cpu().numpy()

    vocals = vocals.T
    wav_path = os.path.join(output_dir, pathlib.Path(mp3_path).stem + "_vocals.wav")
    sf.write(wav_path, vocals, sr)
    print(f"{BLUE}Vocals extracted: {wav_path}{RESET}")
    return wav_path

def detect_vocal_onset(audio_path: str, sr: int = 44100) -> float:
    audio, _ = librosa.load(audio_path, sr=sr, mono=True)
    onset_frames = librosa.onset.onset_detect(y=audio, sr=sr, hop_length=512)
    return onset_frames[0] * 512 / sr if onset_frames.size > 0 else 0.0

def fetch_official_lyrics(title: str, artist: str, album: str, lyrics_path: str, genius: lyricsgenius.Genius) -> list:
    if os.path.exists(lyrics_path) and os.path.getsize(lyrics_path) > 0:
        print(f"{BLUE}Using existing official lyrics: {lyrics_path}{RESET}")
        with open(lyrics_path, "r", encoding="utf-8") as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    
    print(f"{BLUE}Searching for song: {title} by {artist} from album {album}{RESET}")
    query = f"{title} {artist} {album}"
    try:
        song = genius.search_song(title, artist)
        if song and album.lower() in song.album.get('name', '').lower():
            lyrics_lines = [line.strip() for line in song.lyrics.split("\n") if line.strip() and not line.startswith("[")]
            with open(lyrics_path, "w", encoding="utf-8") as f:
                for line in lyrics_lines:
                    f.write(f"{line}\n")
            print(f"{GREEN}Saved official lyrics: {lyrics_path}{RESET}")
            return lyrics_lines
        else:
            songs = genius.search_songs(query)
            best_match = None
            best_score = 0.0
            for hit in songs.get("hits", []):
                song_info = hit.get("result", {})
                song_title = song_info.get("title", "").lower()
                song_artist = song_info.get("primary_artist", {}).get("name", "").lower()
                song_album = song_info.get("album", {}).get("name", "").lower() if song_info.get("album") else ""
                title_score = difflib.SequenceMatcher(None, title.lower(), song_title).ratio()
                artist_score = difflib.SequenceMatcher(None, artist.lower(), song_artist).ratio()
                album_score = difflib.SequenceMatcher(None, album.lower(), song_album).ratio() if album and song_album else 0.5
                total_score = 0.4 * title_score + 0.4 * artist_score + 0.2 * album_score
                if total_score > best_score and total_score > 0.7:
                    best_score = total_score
                    best_match = song_info.get("id")
            if best_match:
                song = genius.get_song(best_match)
                if song and song.get("song"):
                    lyrics_lines = [line.strip() for line in song["song"]["lyrics"].split("\n") if line.strip() and not line.startswith("[")]
                    with open(lyrics_path, "w", encoding="utf-8") as f:
                        for line in lyrics_lines:
                            f.write(f"{line}\n")
                    print(f"{GREEN}Saved official lyrics (matched via search): {lyrics_path}{RESET}")
                    return lyrics_lines
    except Exception as e:
        print(f"{RED}Error fetching lyrics: {e}{RESET}")
    
    print(f"{YELLOW}{BRIGHT}Could not fetch lyrics{RESET} for {YELLOW}{title} by {artist} from {album}{RESET}, skipping track.")
    return []

# -------------------------------
# Whisper model
# -------------------------------
model = "medium.en"
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"{MAGENTA}Loading Whisper {model} model on {device.upper()}...{RESET}")
model = whisper.load_model(model, device=device)

# -------------------------------
# Genius API setup
# -------------------------------
import sys
sys.path.append(str(BASE_DIR.parent))
from utilities import read_json

config_path = BASE_DIR.parent.parent / "config" / "api.config"
api_config = read_json(config_path)
GENIUS_TOKEN = api_config['genius']['access_token']
genius = lyricsgenius.Genius(GENIUS_TOKEN)

# -------------------------------
# Main function
# -------------------------------
def main(input_dir: str) -> None:
    output_dir_synced_lyrics = input_dir
    output_dir_vocals = os.path.join(BASE_DIR, "temp", "vocals")
    output_dir_generated_lyrics = os.path.join(BASE_DIR, "temp", "transcripts")
    output_dir_official_lyrics = os.path.join(input_dir, "Official Lyrics")

    os.makedirs(output_dir_synced_lyrics, exist_ok=True)
    os.makedirs(output_dir_vocals, exist_ok=True)
    os.makedirs(output_dir_generated_lyrics, exist_ok=True)
    os.makedirs(output_dir_official_lyrics, exist_ok=True)

    for file in os.listdir(input_dir):
        if not file.lower().endswith(".mp3"):
            continue

        filepath = os.path.join(input_dir, file)
        lrc_path = os.path.join(output_dir_synced_lyrics, pathlib.Path(file).stem + ".lrc")
        lyrics_path = os.path.join(output_dir_official_lyrics, pathlib.Path(file).stem + "_official_lyrics.txt")

        print(f"{GREEN}{BRIGHT}Processing{RESET}: {filepath}")

        try:
            audio = MP3(filepath, ID3=ID3)
            title = audio.get("TIT2", pathlib.Path(file).stem).text[0]
            artist = audio.get("TPE1", "Of Monsters And Men").text[0]
            album = audio.get("TALB", "Unknown Album").text[0]
            song_duration = audio.info.length
            print(f"{BLUE}Metadata - Title: {title}, Artist: {artist}, Album: {album}, Duration: {song_duration:.2f}s{RESET}")
        except Exception as e:
            print(f"{YELLOW}Could not read metadata: {e}, using filename{RESET}")
            title = pathlib.Path(file).stem
            artist = "Of Monsters And Men"
            album = "Unknown Album"
            song_duration = 300.0

        lyrics_lines = fetch_official_lyrics(title, artist, album, lyrics_path, genius)
        print(f"{BLUE}Official lyrics lines count: {len(lyrics_lines)}{RESET}")
        if not lyrics_lines:
            print(f"{YELLOW}Skipping {file}: No official lyrics available{RESET}")
            continue

        if os.path.exists(lrc_path):
            print(f"{YELLOW}Skipping further processing for {file}: LRC file already exists at {lrc_path}{RESET}")
            continue

        vocals_path = os.path.join(output_dir_vocals, pathlib.Path(filepath).stem + "_vocals.wav")
        if os.path.exists(vocals_path):
            print(f"{BLUE}Vocals file exists, skipping extraction: {vocals_path}{RESET}")
        else:
            try:
                vocals_path = isolate_vocals_demucs(filepath, output_dir_vocals)
                print(f"{BLUE}Vocals extracted: {vocals_path}{RESET}")
            except Exception as e:
                print(f"{RED}Failed to extract vocals, converting to WAV: {e}{RESET}")
                wav_path = os.path.join(output_dir_vocals, pathlib.Path(filepath).stem + ".wav")
                convert_to_wav(filepath, wav_path)
                vocals_path = wav_path

        preprocessed_vocals = vocals_path.replace("_vocals.wav", "_preprocessed_vocals.wav")
        try:
            preprocess_vocals(vocals_path, preprocessed_vocals)
            vocals_path = preprocessed_vocals
            print(f"{BLUE}Preprocessed vocals: {vocals_path}{RESET}")
        except Exception as e:
            print(f"{YELLOW}Vocals preprocessing failed, using original vocals: {e}{RESET}")

        energy_onset = detect_vocal_onset(vocals_path)
        print(f"{BLUE}Energy-based vocal onset: {format_timestamp(energy_onset)}{RESET}")

        try:
            result = model.transcribe(
                vocals_path,
                verbose=False,
                language="en",
                task="transcribe",
                word_timestamps=True,
                beam_size=10,
                best_of=10,
                logprob_threshold=-2.0,
                condition_on_previous_text=False
            )
            whisper_segments = []
            for seg_idx, seg in enumerate(result["segments"]):
                text = seg["text"].strip()
                confidence = seg.get("avg_logprob", -1.0)
                if not text or len(text) <= 3 or confidence < -2.0:
                    continue
                sentences = nltk.sent_tokenize(text)
                words = seg.get("words", [])
                word_times = [(w["start"], w["end"], w["word"]) for w in words if "start" in w and "end" in w]
                if not word_times:
                    duration = seg["end"] - seg["start"]
                    num_splits = len(sentences)
                    if num_splits > 1:
                        time_per_split = duration / num_splits
                        for i, sentence in enumerate(sentences):
                            start_time = seg["start"] + i * time_per_split
                            if sentence.strip():
                                whisper_segments.append((start_time, sentence.strip(), seg_idx))
                    else:
                        whisper_segments.append((seg["start"], text, seg_idx))
                else:
                    current_sentence = 0
                    current_words = []
                    current_start = seg["start"]
                    for start, end, word in word_times:
                        current_words.append(word)
                        if current_sentence < len(sentences) and (word.endswith((".", "!", "?")) or (end - start > 0.5)):
                            sentence_text = " ".join(current_words).strip()
                            if sentence_text:
                                whisper_segments.append((current_start, sentence_text, seg_idx))
                            current_words = []
                            current_start = end
                            current_sentence += 1
                    if current_words and current_sentence <= len(sentences):
                        sentence_text = " ".join(current_words).strip()
                        if sentence_text:
                            whisper_segments.append((current_start, sentence_text, seg_idx))

            print(f"{BLUE}Whisper segments count: {len(whisper_segments)}{RESET}")
            if whisper_segments:
                print(f"{BLUE}Sample Whisper segments: {whisper_segments[:5]}{RESET}")
            else:
                print(f"{RED}Warning: No Whisper segments generated{RESET}")
                print(f"{YELLOW}Trying transcription with original MP3{RESET}")
                try:
                    wav_path = os.path.join(output_dir_vocals, pathlib.Path(filepath).stem + "_original.wav")
                    if not os.path.exists(wav_path):
                        convert_to_wav(filepath, wav_path)
                    preprocessed_wav = wav_path.replace("_original.wav", "_preprocessed_original.wav")
                    try:
                        preprocess_vocals(wav_path, preprocessed_wav)
                        wav_path = preprocessed_wav
                        print(f"{BLUE}Preprocessed fallback audio: {wav_path}{RESET}")
                    except Exception as e:
                        print(f"{YELLOW}Fallback audio preprocessing failed, using original WAV: {e}{RESET}")
                    result = model.transcribe(
                        wav_path,
                        verbose=False,
                        language="en",
                        task="transcribe",
                        word_timestamps=True,
                        beam_size=10,
                        best_of=10,
                        logprob_threshold=-2.0,
                        condition_on_previous_text=False
                    )
                    whisper_segments = []
                    for seg_idx, seg in enumerate(result["segments"]):
                        text = seg["text"].strip()
                        confidence = seg.get("avg_logprob", -1.0)
                        if not text or len(text) <= 3 or confidence < -2.0:
                            continue
                        sentences = nltk.sent_tokenize(text)
                        words = seg.get("words", [])
                        word_times = [(w["start"], w["end"], w["word"]) for w in words if "start" in w and "end" in w]
                        if not word_times:
                            duration = seg["end"] - seg["start"]
                            num_splits = len(sentences)
                            if num_splits > 1:
                                time_per_split = duration / num_splits
                                for i, sentence in enumerate(sentences):
                                    start_time = seg["start"] + i * time_per_split
                                    if sentence.strip():
                                        whisper_segments.append((start_time, sentence.strip(), seg_idx))
                            else:
                                whisper_segments.append((seg["start"], text, seg_idx))
                        else:
                            current_sentence = 0
                            current_words = []
                            current_start = seg["start"]
                            for start, end, word in word_times:
                                current_words.append(word)
                                if current_sentence < len(sentences) and (word.endswith((".", "!", "?")) or (end - start > 0.5)):
                                    sentence_text = " ".join(current_words).strip()
                                    if sentence_text:
                                        whisper_segments.append((current_start, sentence_text, seg_idx))
                                    current_words = []
                                    current_start = end
                                    current_sentence += 1
                            if current_words and current_sentence <= len(sentences):
                                sentence_text = " ".join(current_words).strip()
                                if sentence_text:
                                    whisper_segments.append((current_start, sentence_text, seg_idx))
                    print(f"{BLUE}Fallback Whisper segments count: {len(whisper_segments)}{RESET}")
                    if whisper_segments:
                        print(f"{BLUE}Sample fallback Whisper segments: {whisper_segments[:5]}{RESET}")
                except Exception as e:
                    print(f"{RED}Fallback transcription failed: {e}{RESET}")
                    whisper_segments = []

            transcript_path = os.path.join(output_dir_generated_lyrics, pathlib.Path(file).stem + "_whisper_transcript.txt")
            with open(transcript_path, "w", encoding="utf-8") as f:
                for start, text, _ in whisper_segments:
                    f.write(f"{format_timestamp(start)} {text}\n")
            print(f"{GREEN}Saved Whisper transcription: {transcript_path}{RESET}")

        except Exception as e:
            print(f"{RED}Whisper transcription failed: {e}{RESET}")
            whisper_segments = []

        whisper_onset = whisper_segments[0][0] if whisper_segments else float('inf')
        vocal_onset = min(whisper_onset, energy_onset, 15.0)
        if whisper_onset > 30.0:
            print(f"{YELLOW}Whisper onset too late ({format_timestamp(whisper_onset)}), using energy onset: {format_timestamp(vocal_onset)}{RESET}")
        else:
            print(f"{BLUE}Using vocal onset: {format_timestamp(vocal_onset)}{RESET}")

        aligned = []
        used_segments = set()
        potential_matches = []

        refined_segments = []
        for start, text, seg_idx in whisper_segments:
            words = text.split()
            word_times = [(w["start"], w["end"], w["word"]) for w in result["segments"][seg_idx].get("words", []) if "start" in w and "end" in w]
            if word_times and len(words) > 5:
                current_text = []
                current_start = start
                for w_start, w_end, word in word_times:
                    current_text.append(word)
                    if len(current_text) >= 5 or word.endswith((".", "!", "?")) or (w_end - w_start > 0.5):
                        segment_text = " ".join(current_text).strip()
                        if segment_text:
                            refined_segments.append((current_start, segment_text, seg_idx))
                        current_text = []
                        current_start = w_end
                if current_text:
                    segment_text = " ".join(current_text).strip()
                    if segment_text:
                        refined_segments.append((current_start, segment_text, seg_idx))
            else:
                refined_segments.append((start, text, seg_idx))
        whisper_segments = refined_segments

        for lyric_idx, lyric in enumerate(lyrics_lines):
            lyric_norm = normalize(lyric)
            best_match = None
            best_ratio = 0.0
            best_start = 0.0

            threshold = 0.05 if lyric_idx < 5 else 0.15
            is_refrain = is_repetitive(lyric)
            if is_refrain:
                for seg_idx, (start, w_text, orig_idx) in enumerate(whisper_segments):
                    if seg_idx in used_segments or start < vocal_onset:
                        continue
                    if is_repetitive(w_text):
                        best_match = (seg_idx, w_text, orig_idx)
                        best_ratio = 1.0
                        best_start = start
                        break

            if not best_match:
                time_window = 25.0 if lyric_idx < 5 else 10.0
                expected_time = max(vocal_onset, (lyric_idx / len(lyrics_lines)) * song_duration if lyrics_lines else song_duration)
                for seg_idx, (start, w_text, orig_idx) in enumerate(whisper_segments):
                    if seg_idx in used_segments or start < vocal_onset:
                        continue
                    if abs(start - expected_time) > time_window:
                        continue
                    w_norm = normalize(w_text)
                    ratio = difflib.SequenceMatcher(None, w_norm, lyric_norm).ratio()
                    potential_matches.append((w_text, lyric, ratio, start))
                    print(f"{BLUE}Comparing '{w_text}' to '{lyric}': Similarity = {ratio:.3f}, Time = {format_timestamp(start)}{RESET}")
                    if ratio > best_ratio:
                        best_ratio = ratio
                        best_match = (seg_idx, w_text, orig_idx)
                        best_start = start

            if best_match and best_ratio >= threshold:
                seg_idx, w_text, _ = best_match
                aligned.append((best_start, lyric))
                used_segments.add(seg_idx)
                print(f"{GREEN}Matched '{lyric}' to '{w_text}' at {format_timestamp(best_start)} (ratio: {best_ratio:.3f}){RESET}")
            else:
                if aligned:
                    prev_ts = aligned[-1][0]
                    next_ts = song_duration
                    for seg_idx, (start, _, _) in enumerate(whisper_segments):
                        if seg_idx not in used_segments and start > prev_ts:
                            next_ts = start
                            break
                    offset = 1.0 if is_repetitive(lyric) else 2.0
                    estimated_time = prev_ts + offset
                    if lyric_idx < len(lyrics_lines) - 1:
                        estimated_time = min(estimated_time, next_ts - 0.1)
                else:
                    estimated_time = vocal_onset
                estimated_time = max(estimated_time, vocal_onset)
                estimated_time = min(estimated_time, song_duration)
                aligned.append((estimated_time, lyric))
                print(f"{YELLOW}No match for '{lyric}', estimated timestamp: {format_timestamp(estimated_time)}{RESET}")

        final_aligned = []
        for i, (ts, lyric) in enumerate(aligned):
            if i == 0:
                final_aligned.append((max(ts, vocal_onset), lyric))
                continue
            prev_ts = final_aligned[-1][0]
            next_ts = aligned[i+1][0] if i < len(aligned) - 1 else song_duration
            if ts <= prev_ts:
                new_ts = prev_ts + (1.0 if is_repetitive(lyric) else 2.0)
                new_ts = min(new_ts, next_ts - 0.1) if i < len(aligned) - 1 else new_ts
                final_aligned.append((new_ts, lyric))
                print(f"{YELLOW}Adjusted timestamp for '{lyric}' to {format_timestamp(new_ts)} (was {format_timestamp(ts)}){RESET}")
            else:
                final_aligned.append((ts, lyric))

        aligned = final_aligned

        print(f"{BLUE}Aligned lyrics count: {len(aligned)}{RESET}")
        if aligned:
            print(f"{BLUE}Sample aligned lyrics: {aligned[:3]}{RESET}")

        unmatched_segments = [(start, text) for idx, (start, text, _) in enumerate(whisper_segments) if idx not in used_segments]
        if unmatched_segments:
            print(f"{YELLOW}Unmatched Whisper segments:{RESET}")
            for start, text in unmatched_segments:
                print(f"  {format_timestamp(start)} {text}")

        lrc_path = os.path.join(output_dir_synced_lyrics, pathlib.Path(file).stem + ".lrc")
        with open(lrc_path, "w", encoding="utf-8") as f:
            for ts, line in sorted(aligned, key=lambda x: x[0]):
                f.write(f"{format_timestamp(ts)} {line}\n")
        print(f"{GREEN}{BRIGHT}Saved synced lyrics{RESET}: {lrc_path}")

if __name__ == "__main__":
    input_dir = r"A:\Music\MP3s_320\Of Monsters And Men\(2021) My Head Is An Animal (10th Anniversary Edition)"
    main(input_dir)