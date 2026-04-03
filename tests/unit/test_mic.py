"""
Quick test to check microphone and audio devices
"""
import sounddevice as sd
import numpy as np

print("=" * 60)
print("AUDIO DEVICE TEST")
print("=" * 60)

# List all audio devices
print("\n📋 Available Audio Devices:")
print(sd.query_devices())

print("\n" + "=" * 60)

# Get default input device
try:
    default_input = sd.query_devices(kind='input')
    print(f"\n✓ Default Input Device: {default_input['name']}")
    print(f"  - Channels: {default_input['max_input_channels']}")
    print(f"  - Sample Rate: {default_input['default_samplerate']} Hz")
except Exception as e:
    print(f"\n✗ Error getting default input: {e}")

print("\n" + "=" * 60)

# Test recording
print("\n🎤 Testing microphone... (Recording 3 seconds)")
print("SPEAK NOW!")

try:
    SAMPLE_RATE = 16000
    DURATION = 3
    
    recording = sd.rec(
        int(DURATION * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype=np.int16
    )
    sd.wait()
    
    print("\n✓ Recording complete!")
    
    # Analyze recording
    audio_data = recording.flatten()
    max_amplitude = np.max(np.abs(audio_data))
    rms = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))
    
    print(f"\n📊 Audio Analysis:")
    print(f"  - Max Amplitude: {max_amplitude}")
    print(f"  - RMS Energy: {rms:.2f}")
    print(f"  - Duration: {DURATION}s")
    print(f"  - Sample Rate: {SAMPLE_RATE}Hz")
    
    if max_amplitude < 100:
        print(f"\n⚠️  WARNING: Very low audio signal!")
        print("    - Check if microphone is connected and enabled")
        print("    - Check Windows microphone permissions")
        print("    - Increase microphone volume in system settings")
    elif max_amplitude < 500:
        print(f"\n⚠️  Audio signal is weak but present")
        print("    - Consider increasing microphone volume")
    else:
        print(f"\n✓ Audio signal looks good!")
        
except Exception as e:
    print(f"\n✗ Recording failed: {e}")
    print("\nPossible issues:")
    print("  - No microphone connected")
    print("  - Microphone access denied")
    print("  - Wrong audio device selected")

print("\n" + "=" * 60)
print("Test complete!")
print("=" * 60)
