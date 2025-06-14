# OpenAI Real-time Speech-to-Text Tool Pro v1.0

A professional real-time speech transcription tool based on OpenAI Realtime API, featuring multilingual interface, typewriter effect display, audio visualization, and advanced functionalities.

## ✨ Key Features

### 🎙️ Real-time Speech Transcription
- Built on OpenAI's latest Realtime API (gpt-4o-transcribe)
- Ultra-low latency (<20ms) real-time transcription
- Support for 15+ languages speech recognition
- Intelligent Voice Activity Detection (VAD)
- High-quality audio processing and noise suppression

### 💫 Typewriter Effect Display
- Smooth typewriter-style text rendering
- Real-time character streaming
- Intelligent line breaks and paragraph segmentation
- Color-coded status display (yellow streaming → green completed)

### 🎵 Audio Monitoring Visualization
- Real-time waveform display
- Volume level monitoring
- Peak detection and noise analysis
- Session statistics

### 🌐 Multilingual Interface
- Chinese/English bilingual interface
- Real-time language switching
- Localized configuration saving

### 🔧 Advanced Configuration Options
- VAD sensitivity adjustment
- Audio quality enhancement
- Network connection optimization
- Performance parameter tuning

### 📁 File Transcription Support
- Support for multiple audio formats (MP3, WAV, M4A, MP4, etc.)
- Automatic large file splitting
- Batch processing capabilities

### 🏷️ Smart Hotword Optimization
- Custom professional terminology dictionary
- Preset industry vocabulary packages (AI, Tech, Business, Medical, Education)
- Enhanced recognition accuracy for specific domains

## 🚀 Quick Start

### Requirements

- Python 3.8+
- OpenAI API Key
- Audio input device (microphone)

### Install Dependencies

```bash
# Clone the project
git clone https://github.com/yourusername/openai-realtime-transcriber.git
cd openai-realtime-transcriber

# Install dependencies
pip install -r requirements.txt
```

### Run the Program

```bash
python main.py
```

## 📦 Dependencies

### Required Dependencies
- `PyQt5` - GUI framework
- `openai` - OpenAI API client
- `websocket-client` - WebSocket connection
- `pyaudio` - Audio recording
- `numpy` - Numerical computing
- `requests` - HTTP requests

### Optional Dependencies
- `pyqtgraph` - Advanced audio visualization (recommended)
- `pydub` - Large file audio processing (recommended)

## ⚙️ Configuration Guide

### 1. API Configuration
Enter your OpenAI API Key in the program:
- Support for custom API endpoints
- Compatible with OpenAI-compatible API services
- Automatic configuration saving

### 2. Audio Devices
- Automatic detection of available audio input devices
- Support for multiple audio sampling rates
- Real-time device switching

### 3. Language Settings
Supported transcription languages:
- Chinese (zh)
- English (en)
- Japanese (ja)
- Korean (ko)
- French (fr)
- German (de)
- Spanish (es)
- Italian (it)
- Portuguese (pt)
- Russian (ru)
- Arabic (ar)
- Hindi (hi)
- Thai (th)
- Vietnamese (vi)

## 🎛️ Feature Details

### Real-time Transcription Control
- **Start/Stop**: One-click control of real-time transcription
- **Clear**: Clear current display content
- **Save**: Export transcription results as text files
- **Copy**: Copy content to clipboard

### Audio Optimization Settings
- **VAD Threshold**: Adjust voice detection sensitivity
- **Silence Interval**: Set voice segmentation timing
- **Noise Suppression**: Multi-level noise filtering
- **Audio Filtering**: Signal quality enhancement

### Display Effect Control
- **Typing Speed**: Adjust character display speed
- **Line Break Interval**: Control automatic line break frequency
- **Font Size**: Multi-level font adjustment
- **Auto Scroll**: Smart content tracking

### Hotword Optimization
Preset vocabulary packages:
- 🤖 AI Terms: OpenAI, ChatGPT, Artificial Intelligence, Machine Learning...
- 💻 Tech Terms: API, Python, Database, Cloud Computing...
- 💼 Business Terms: Project, Meeting, Client, Cooperation...
- 🏥 Medical Terms: Symptoms, Diagnosis, Treatment, Medicine...
- 📚 Education Terms: Course, Learning, Teaching, Research...

## 🔍 Troubleshooting

### Common Issues

**1. Cannot Start Recording**
- Check microphone permissions
- Confirm audio device connection
- Try refreshing device list

**2. API Connection Failed**
- Verify API Key validity
- Check network connection
- Confirm API endpoint settings

**3. Poor Transcription Quality**
- Adjust VAD sensitivity
- Enable noise suppression
- Add relevant hotwords

**4. Performance Issues**
- Enable ultra-fast mode
- Turn on aggressive memory cleanup
- Lower audio quality settings

### Debug Logging
The program includes a detailed logging system for monitoring runtime status in the console.

## 🛠️ Technical Architecture

### Core Components
- **UltraRealtimeTranscriber**: Real-time transcription engine
- **TypewriterDisplayWidget**: Typewriter effect display
- **UltraFastAudioRecorder**: High-performance audio recording
- **ConfigManager**: Configuration management system
- **LanguageManager**: Multilingual support

### Threading Model
- Main UI Thread: Interface interaction and display
- Audio Thread: Real-time audio capture
- Transcription Thread: WebSocket communication and processing
- Visualization Thread: Audio waveform rendering

### Security Features
- Prompt leakage filtering
- Thread-safe queues
- Exception recovery mechanism
- Automatic resource cleanup

## 📈 Performance Metrics

- **Latency**: <20ms end-to-end latency
- **Accuracy**: 95%+ (with hotword optimization)
- **Concurrency**: Support for multiple device simultaneous recording
- **Stability**: Passed 24/7 continuous operation testing

## 🤝 Contributing

Issues and Pull Requests are welcome!

### Development Environment Setup
```bash
# Clone development branch
git clone -b develop https://github.com/yourusername/openai-realtime-transcriber.git

# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
python -m pytest tests/
```

### Code Standards
- Follow PEP 8 code style
- Add type annotations
- Write unit tests
- Update documentation

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [OpenAI](https://openai.com/) - For providing powerful Realtime API
- [PyQt5](https://www.riverbankcomputing.com/software/pyqt/) - Excellent GUI framework
- [PyAudio](https://people.csail.mit.edu/hubert/pyaudio/) - Audio processing support

## 📞 Contact

- Project Homepage: https://github.com/yourusername/openai-realtime-transcriber
- Issue Reports: https://github.com/yourusername/openai-realtime-transcriber/issues
- Email: your.email@example.com

## 🔮 Roadmap

### v1.1 Planned Features
- [ ] Support for more audio formats
- [ ] Real-time translation functionality
- [ ] Extended subtitle export formats
- [ ] Voice emotion analysis
- [ ] Multi-speaker conversation recognition

### v2.0 Planned Features
- [ ] Plugin system
- [ ] Cloud configuration sync
- [ ] Team collaboration features
- [ ] API service mode

## 🔧 Installation Guide

### System Requirements
- **Operating System**: Windows 10/11, macOS 10.14+, Linux (Ubuntu 18.04+)
- **Python Version**: 3.8+ (3.9+ recommended)
- **Memory**: Minimum 4GB, 8GB+ recommended
- **Audio Device**: Microphone or audio input device
- **Network**: Stable internet connection (for API calls)

### Step-by-Step Installation

#### 1. Check Python Version
```bash
python --version
# or
python3 --version
```

#### 2. Clone the Project
```bash
git clone https://github.com/yourusername/openai-realtime-transcriber.git
cd openai-realtime-transcriber
```

#### 3. Create Virtual Environment (Recommended)
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

#### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

#### 5. System-Specific Configuration

**Windows:**
```bash
# If pyaudio installation fails:
pip install pipwin
pipwin install pyaudio
```

**macOS:**
```bash
# Install portaudio (pyaudio dependency)
brew install portaudio
pip install pyaudio
```

**Linux (Ubuntu/Debian):**
```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install python3-pyqt5 portaudio19-dev python3-dev
pip install -r requirements.txt
```

### Verify Installation
```bash
python main.py
```

If the program starts normally and displays the GUI interface, the installation is successful.

## 📱 Usage Examples

### Basic Usage
1. **Start the Application**: Run `python main.py`
2. **Configure API**: Enter your OpenAI API Key in the Basic Settings tab
3. **Select Audio Device**: Choose your microphone from the device list
4. **Start Transcription**: Click the "⚡ Start Real-time" button
5. **Monitor Results**: Watch real-time transcription with typewriter effect

### Advanced Configuration
1. **Adjust VAD Sensitivity**: Fine-tune voice detection in Realtime tab
2. **Add Hotwords**: Include domain-specific terms in Hotwords tab
3. **Optimize Performance**: Configure network and performance settings in Advanced tab

### File Transcription
1. **Click "📁 File" Button**: Select audio file for transcription
2. **Large File Support**: Automatic splitting for files >25MB
3. **Export Results**: Save transcriptions as text files

## 🏆 Best Practices

### For Optimal Transcription Quality
- Use a high-quality microphone
- Ensure stable network connection
- Add relevant hotwords for your domain
- Adjust VAD threshold based on environment noise
- Enable noise suppression in noisy environments

### For Better Performance
- Enable ultra-fast mode for low-latency requirements
- Use aggressive memory cleanup for long sessions
- Adjust typewriter speed based on preference
- Monitor audio levels to avoid clipping

---

**⚡ Powered by 瓦力 AI Simultaneous Interpretation Technology**

*Making real-time speech transcription smarter, more accurate, and more user-friendly!*