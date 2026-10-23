// Browser Text-to-Speech (TTS) helper for realistic voice playback

export function playSpeech(text, language = "English") {
  if (!("speechSynthesis" in window)) {
    console.warn("Speech synthesis not supported in this browser.");
    return false;
  }

  window.speechSynthesis.cancel(); // Stop any active utterance

  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 1.0;
  utterance.pitch = 1.0;

  // Language mapping
  const langLower = language.toLowerCase();
  if (langLower.includes("hindi")) {
    utterance.lang = "hi-IN";
  } else if (langLower.includes("kannada")) {
    utterance.lang = "kn-IN";
  } else if (langLower.includes("tamil")) {
    utterance.lang = "ta-IN";
  } else if (langLower.includes("telugu")) {
    utterance.lang = "te-IN";
  } else {
    utterance.lang = "en-IN";
  }

  // Look for a voice matching the language if available
  const voices = window.speechSynthesis.getVoices();
  const matchedVoice = voices.find((v) => v.lang.startsWith(utterance.lang.slice(0, 2)));
  if (matchedVoice) {
    utterance.voice = matchedVoice;
  }

  window.speechSynthesis.speak(utterance);
  return true;
}

export function stopSpeech() {
  if ("speechSynthesis" in window) {
    window.speechSynthesis.cancel();
  }
}
