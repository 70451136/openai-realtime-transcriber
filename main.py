import sys
import pyaudio
import wave
import threading
import time
import queue
import tempfile
import os
import asyncio
import json
import numpy as np
import base64
import websocket
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout,
                             QHBoxLayout, QWidget, QPushButton, QTextEdit,
                             QLabel, QLineEdit, QScrollArea, QSpinBox, QCheckBox,
                             QComboBox, QSlider, QGroupBox, QTextBrowser,
                             QTabWidget, QProgressBar, QFileDialog, QMessageBox,
                             QFrame, QSplitter, QDesktopWidget, QGridLayout)
from PyQt5.QtCore import QThread, pyqtSignal, QTimer, Qt, QPropertyAnimation, QEasingCurve, QRect, QMutex, QMutexLocker
from PyQt5.QtGui import QFont, QTextCursor, QColor, QPainter, QPen, QBrush, QLinearGradient, QTextCharFormat
import openai
import requests
import difflib
import traceback
import logging

try:
    import pyqtgraph as pg

    HAS_PYQTGRAPH = True
except ImportError:
    HAS_PYQTGRAPH = False
    print("PyQtGraph未安装，将使用简化的音频可视化")

try:
    from pydub import AudioSegment

    HAS_PYDUB = True
except ImportError:
    HAS_PYDUB = False
    print("pydub未安装，大文件分割功能将受限")

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ConfigManager:
    """配置管理器 - 处理配置保存和加载"""

    def __init__(self):
        self.config_file = os.path.join(os.path.expanduser("~"), ".openai_asr_config.json")
        self.default_config = {
            'ui_language': 'zh',
            'api_key': '',
            'base_url': 'https://api.openai.com/v1',
            'model': 'gpt-4o-transcribe',
            'language': 'zh',
            'prompt': '',
            'hotwords': [],
            'font_size': 18
        }

    def load_config(self):
        """加载配置"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 合并默认配置，确保所有字段都存在
                    for key, value in self.default_config.items():
                        if key not in config:
                            config[key] = value
                    return config
            return self.default_config.copy()
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            return self.default_config.copy()

    def save_config(self, config):
        """保存配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False


class LanguageManager:
    """语言管理器 - 支持界面多语言"""

    def __init__(self):
        self.current_language = 'zh'  # 默认中文
        self.languages = {
            'zh': '中文',
            'en': 'English'
        }

        # 完整的语言映射字典
        self.texts = {
            # 窗口标题
            'window_title': {
                'zh': 'OpenAI 实时语音转文字工具 Pro v1.0',
                'en': 'OpenAI Real-time Speech-to-Text Tool Pro v1.0'
            },

            # 主标题
            'main_title': {
                'zh': '⚡ 实时ASR控制中心 v1.0',
                'en': '⚡ Real-time ASR Control v1.0'
            },

            # 广告标签
            'tech_support': {
                'zh': '软件由瓦力AI同声传译字幕技术支持',
                'en': 'Powered by 瓦力 AI Simultaneous Interpretation'
            },

            # 标签页标题
            'tab_basic': {
                'zh': '🔧 基本设置',
                'en': '🔧 Basic'
            },
            'tab_realtime': {
                'zh': '⚡ 实时优化',
                'en': '⚡ Realtime'
            },
            'tab_hotwords': {
                'zh': '🏷️ 热词',
                'en': '🏷️ Keywords'
            },
            'tab_advanced': {
                'zh': '⚙️ 高级',
                'en': '⚙️ Advanced'
            },

            # 组框标题
            'group_language': {
                'zh': '🌐 界面语言',
                'en': '🌐 UI Language'
            },
            'group_api': {
                'zh': '🔑 API 配置',
                'en': '🔑 API Config'
            },
            'group_device': {
                'zh': '🎙️ 音频设备',
                'en': '🎙️ Audio Device'
            },
            'group_prompt': {
                'zh': '📝 转录提示词',
                'en': '📝 Transcription Prompt'
            },
            'group_vad': {
                'zh': '⚡ 语音检测优化',
                'en': '⚡ Voice Detection'
            },
            'group_audio_enhance': {
                'zh': '🎵 音频质量增强',
                'en': '🎵 Audio Enhancement'
            },
            'group_display': {
                'zh': '⌨️ 显示控制',
                'en': '⌨️ Display Control'
            },
            'group_hotwords': {
                'zh': '🏷️ 热词优化列表',
                'en': '🏷️ Keyword List'
            },
            'group_usage': {
                'zh': '📖 使用说明',
                'en': '📖 Usage Guide'
            },
            'group_network': {
                'zh': '🌐 网络设置',
                'en': '🌐 Network Settings'
            },
            'group_performance': {
                'zh': '🚀 性能优化',
                'en': '🚀 Performance'
            },
            'group_debug': {
                'zh': '🔍 调试信息',
                'en': '🔍 Debug Info'
            },

            # 标签文本
            'label_language': {
                'zh': '界面语言:',
                'en': 'Language:'
            },
            'label_api_key': {
                'zh': 'API Key:',
                'en': 'API Key:'
            },
            'label_endpoint': {
                'zh': '端点:',
                'en': 'Endpoint:'
            },
            'label_model': {
                'zh': '模型:',
                'en': 'Model:'
            },
            'label_language_model': {
                'zh': '语言:',
                'en': 'Lang:'
            },
            'label_device': {
                'zh': '输入设备:',
                'en': 'Input Device:'
            },
            'label_sensitivity': {
                'zh': '检测灵敏度:',
                'en': 'Sensitivity:'
            },
            'label_silence_interval': {
                'zh': '静音间隔 (ms):',
                'en': 'Silence (ms):'
            },
            'label_noise_reduction': {
                'zh': '噪音抑制级别:',
                'en': 'Noise Reduction:'
            },
            'label_line_break': {
                'zh': '换行间隔 (句数):',
                'en': 'Line Break:'
            },
            'label_typing_speed': {
                'zh': '打字速度:',
                'en': 'Typing Speed:'
            },
            'label_timeout': {
                'zh': '连接超时 (秒):',
                'en': 'Timeout (s):'
            },
            'label_reconnect': {
                'zh': '最大重连次数:',
                'en': 'Max Reconnect:'
            },

            # 按钮文本
            'btn_start': {
                'zh': '⚡ 开始实时转录',
                'en': '⚡ Start Real-time'
            },
            'btn_stop': {
                'zh': '⏹️ 停止转录',
                'en': '⏹️ Stop'
            },
            'btn_clear': {
                'zh': '🗑️ 清空',
                'en': '🗑️ Clear'
            },
            'btn_save': {
                'zh': '💾 保存',
                'en': '💾 Save'
            },
            'btn_load_file': {
                'zh': '📁 文件转录',
                'en': '📁 File'
            },
            'btn_copy': {
                'zh': '📋 复制',
                'en': '📋 Copy'
            },
            'btn_export': {
                'zh': '📤 导出',
                'en': '📤 Export'
            },
            'btn_settings': {
                'zh': '⚙️ 设置',
                'en': '⚙️ Settings'
            },
            'btn_refresh': {
                'zh': '🔄 刷新',
                'en': '🔄 Refresh'
            },
            'btn_auto_scroll': {
                'zh': '📜 自动滚动',
                'en': '📜 Auto Scroll'
            },
            'btn_font': {
                'zh': '🔤 字体',
                'en': '🔤 Font'
            },

            # 预设按钮
            'btn_general': {
                'zh': '📋 通用',
                'en': '📋 General'
            },
            'btn_tech': {
                'zh': '💻 技术',
                'en': '💻 Tech'
            },
            'btn_business': {
                'zh': '💼 商务',
                'en': '💼 Business'
            },
            'btn_medical': {
                'zh': '🏥 医疗',
                'en': '🏥 Medical'
            },
            'btn_education': {
                'zh': '📚 教育',
                'en': '📚 Education'
            },
            'btn_ai_words': {
                'zh': '🤖 AI词汇',
                'en': '🤖 AI Terms'
            },
            'btn_tech_words': {
                'zh': '💻 技术词汇',
                'en': '💻 Tech Terms'
            },
            'btn_business_words': {
                'zh': '💼 商务词汇',
                'en': '💼 Business'
            },
            'btn_medical_words': {
                'zh': '🏥 医疗词汇',
                'en': '🏥 Medical'
            },
            'btn_edu_words': {
                'zh': '📚 教育词汇',
                'en': '📚 Education'
            },

            # 复选框文本
            'checkbox_audio_filter': {
                'zh': '启用音频滤波器',
                'en': 'Enable Audio Filter'
            },
            'checkbox_noise_gate': {
                'zh': '启用噪音门限',
                'en': 'Enable Noise Gate'
            },
            'checkbox_ultra_mode': {
                'zh': '启用超快模式',
                'en': 'Enable Ultra Mode'
            },
            'checkbox_aggressive_cleanup': {
                'zh': '激进内存清理',
                'en': 'Aggressive Cleanup'
            },
            'checkbox_debug_mode': {
                'zh': '启用调试模式',
                'en': 'Enable Debug Mode'
            },

            # 占位符文本
            'placeholder_api_key': {
                'zh': '请输入OpenAI API Key',
                'en': 'Enter OpenAI API Key'
            },
            'placeholder_prompt': {
                'zh': '例如：请准确转录技术会议内容，注意专业术语的准确性...',
                'en': 'e.g.: Please accurately transcribe technical content...'
            },
            'placeholder_hotwords': {
                'zh': '每行一个热词，例如：\nOpenAI\nChatGPT\n人工智能\n实时转录\n机器学习\n深度学习',
                'en': 'One keyword per line, e.g.:\nOpenAI\nChatGPT\nAI\nReal-time\nMachine Learning\nDeep Learning'
            },

            # 帮助文本
            'help_prompt': {
                'zh': '自定义提示词可以提高特定领域的转录准确度：',
                'en': 'Custom prompts can improve transcription accuracy:'
            },
            'help_hotwords': {
                'zh': '添加专业词汇可以提高识别准确度，每行一个词汇：',
                'en': 'Add professional terms to improve accuracy, one per line:'
            },

            # 状态文本
            'status_ready': {
                'zh': '就绪',
                'en': 'Ready'
            },
            'status_starting': {
                'zh': '⚡ 启动实时ASR中...',
                'en': '⚡ Starting ASR...'
            },
            'status_stopped': {
                'zh': '⏹️ 已停止',
                'en': '⏹️ Stopped'
            },
            'status_cleared': {
                'zh': '🗑️ 已清空',
                'en': '🗑️ Cleared'
            },
            'status_saved': {
                'zh': '💾 已保存',
                'en': '💾 Saved'
            },
            'status_copied': {
                'zh': '📋 已复制到剪贴板',
                'en': '📋 Copied'
            },
            'status_device_updated': {
                'zh': '🔄 设备已更新',
                'en': '🔄 Device Updated'
            },
            'status_no_content': {
                'zh': '❌ 无内容可保存',
                'en': '❌ No Content'
            },
            'status_api_key_required': {
                'zh': '❌ 请输入API Key',
                'en': '❌ API Key Required'
            },
            'status_preset_prompt_set': {
                'zh': '📝 已设置预设提示词',
                'en': '📝 Preset Applied'
            },
            'status_font_size': {
                'zh': '🔤 字体大小',
                'en': '🔤 Font Size'
            },
            'status_language_changed': {
                'zh': '🌐 界面语言已切换',
                'en': '🌐 Language Changed'
            },

            # 指示器文本
            'indicator_ready': {
                'zh': '🟡 实时ASR准备就绪',
                'en': '🟡 Real-time ASR Ready'
            },
            'indicator_active': {
                'zh': '⚡ 实时ASR已激活',
                'en': '⚡ Real-time ASR Active'
            },
            'indicator_stopped': {
                'zh': '🔴 实时ASR已停止',
                'en': '🔴 Real-time ASR Stopped'
            },
            'indicator_connecting': {
                'zh': '🔄 建立连接...',
                'en': '🔄 Connecting...'
            },
            'indicator_connected': {
                'zh': '⚡ 已连接',
                'en': '⚡ Connected'
            },
            'indicator_disconnected': {
                'zh': '🔌 连接断开',
                'en': '🔌 Disconnected'
            },
            'indicator_error': {
                'zh': '❌ 连接错误',
                'en': '❌ Error'
            },
            'indicator_not_connected': {
                'zh': '🔴 未连接',
                'en': '🔴 Not Connected'
            },
            'indicator_speech_detected': {
                'zh': '⚡ 检测到语音',
                'en': '⚡ Speech Detected'
            },
            'indicator_speech_ended': {
                'zh': '⏸️ 语音结束',
                'en': '⏸️ Speech Ended'
            },
            'indicator_waiting': {
                'zh': '💬 等待语音',
                'en': '💬 Waiting'
            },
            'indicator_typing': {
                'zh': '💬 正在打字...',
                'en': '💬 Typing...'
            },

            # 音频监控
            'audio_monitor_title': {
                'zh': '🎵 音频监控',
                'en': '🎵 Audio Monitor'
            },
            'audio_waveform': {
                'zh': '📊 实时波形',
                'en': '📊 Waveform'
            },
            'audio_volume': {
                'zh': '🔊 音量',
                'en': '🔊 Volume'
            },
            'audio_stats': {
                'zh': '📈 统计',
                'en': '📈 Stats'
            },
            'audio_quiet': {
                'zh': '安静',
                'en': 'Quiet'
            },
            'audio_normal': {
                'zh': '正常',
                'en': 'Normal'
            },
            'audio_noisy': {
                'zh': '嘈杂',
                'en': 'Noisy'
            },
            'audio_peak': {
                'zh': '峰值',
                'en': 'Peak'
            },
            'audio_chars': {
                'zh': '字符',
                'en': 'Chars'
            },

            # 字幕显示
            'subtitle_title': {
                'zh': '⚡ 智能实时转录',
                'en': '⚡ Smart Real-time Transcription'
            },
            'subtitle_delay': {
                'zh': '延迟',
                'en': 'Delay'
            },
            'subtitle_word_count': {
                'zh': '字数',
                'en': 'Words'
            },
            'subtitle_active_items': {
                'zh': '活跃项',
                'en': 'Active'
            },
            'subtitle_format': {
                'zh': '格式: 实时ASR',
                'en': 'Format: Real-time ASR'
            },

            # 对话框
            'dialog_config_error': {
                'zh': '配置错误',
                'en': 'Config Error'
            },
            'dialog_api_key_required': {
                'zh': '请先输入您的OpenAI API Key',
                'en': 'Please enter your OpenAI API Key first'
            },
            'dialog_start_transcription': {
                'zh': '开始实时转录',
                'en': 'Start Real-time'
            },
            'dialog_clear_content': {
                'zh': '是否清空当前显示的内容？',
                'en': 'Clear current content?'
            },
            'dialog_clear_confirm': {
                'zh': '清空确认',
                'en': 'Clear Confirm'
            },
            'dialog_clear_all': {
                'zh': '确定要清空所有转录内容吗？',
                'en': 'Clear all transcription content?'
            },
            'dialog_no_content_save': {
                'zh': '当前没有转录内容可保存',
                'en': 'No transcription content to save'
            },
            'dialog_save_success': {
                'zh': '保存成功',
                'en': 'Save Success'
            },
            'dialog_save_to': {
                'zh': '转录内容已保存到',
                'en': 'Transcription saved to'
            },
            'dialog_settings_info': {
                'zh': '设置功能已集成在左侧标签页中，请在对应标签页调整参数。',
                'en': 'Settings are integrated in the left tabs. Please adjust parameters in the corresponding tabs.'
            },
            'dialog_tip': {
                'zh': '提示',
                'en': 'Tip'
            },
            'dialog_settings': {
                'zh': '设置',
                'en': 'Settings'
            },
            'dialog_error': {
                'zh': '错误',
                'en': 'Error'
            },
            'dialog_api_error': {
                'zh': 'API错误',
                'en': 'API Error'
            },
            'dialog_program_error': {
                'zh': '程序错误',
                'en': 'Program Error'
            },
            'dialog_unexpected_error': {
                'zh': '发生未预期的错误',
                'en': 'Unexpected error occurred'
            },
            'dialog_error_logged': {
                'zh': '详细信息已记录到日志。',
                'en': 'Details logged.'
            },
            'dialog_too_many_errors': {
                'zh': '错误过多，程序将退出。请检查配置和网络连接。',
                'en': 'Too many errors. Please check configuration and network.'
            },

            # 文件对话框
            'file_save_transcription': {
                'zh': '保存转录文件',
                'en': 'Save Transcription'
            },
            'file_select_audio': {
                'zh': '选择音频文件',
                'en': 'Select Audio File'
            },
            'file_audio_files': {
                'zh': '音频文件 (*.mp3 *.wav *.m4a *.mp4 *.mpeg *.mpga *.webm *.flac *.aac)',
                'en': 'Audio Files (*.mp3 *.wav *.m4a *.mp4 *.mpeg *.mpga *.webm *.flac *.aac)'
            },
            'file_text_files': {
                'zh': '文本文件 (*.txt)',
                'en': 'Text Files (*.txt)'
            },
            'file_all_files': {
                'zh': '所有文件 (*)',
                'en': 'All Files (*)'
            },

            # 语言选项
            'language_auto': {
                'zh': '自动检测',
                'en': 'Auto Detect'
            },
            'language_chinese': {
                'zh': '中文',
                'en': 'Chinese'
            },
            'language_english': {
                'zh': '英语',
                'en': 'English'
            },
            'language_japanese': {
                'zh': '日语',
                'en': 'Japanese'
            },
            'language_korean': {
                'zh': '韩语',
                'en': 'Korean'
            },
            'language_french': {
                'zh': '法语',
                'en': 'French'
            },
            'language_german': {
                'zh': '德语',
                'en': 'German'
            },
            'language_spanish': {
                'zh': '西班牙语',
                'en': 'Spanish'
            },
            'language_italian': {
                'zh': '意大利语',
                'en': 'Italian'
            },
            'language_portuguese': {
                'zh': '葡萄牙语',
                'en': 'Portuguese'
            },
            'language_russian': {
                'zh': '俄语',
                'en': 'Russian'
            },
            'language_arabic': {
                'zh': '阿拉伯语',
                'en': 'Arabic'
            },
            'language_hindi': {
                'zh': '印地语',
                'en': 'Hindi'
            },
            'language_thai': {
                'zh': '泰语',
                'en': 'Thai'
            },
            'language_vietnamese': {
                'zh': '越南语',
                'en': 'Vietnamese'
            },

            # 使用说明
            'usage_text': {
                'zh': '''
• 热词功能可以提高特定词汇的识别准确度
• 建议添加会议中经常出现的专业术语、人名、地名等
• 每个热词单独一行，支持中英文混合
• 热词数量建议控制在30个以内，过多可能影响性能
• 可以根据不同场景选择相应的预设词汇包
            ''',
                'en': '''
• Keywords improve recognition accuracy for specific terms
• Add professional terms, names, places frequently used
• One keyword per line, supports mixed languages
• Limit to 30 keywords for optimal performance
• Choose preset packages for different scenarios
            '''
            },

            # 预设提示词
            'preset_general': {
                'zh': '请提供准确、流畅的实时转录。保持标点符号和语法正确。优先识别常用词汇和专业术语。',
                'en': 'Provide accurate, fluent real-time transcription. Maintain proper punctuation and grammar.'
            },
            'preset_tech': {
                'zh': '请准确转录技术内容，注意API、框架、编程语言等专业术语的准确性。保持技术名词的原文形式。',
                'en': 'Accurately transcribe technical content. Pay attention to APIs, frameworks, programming languages.'
            },
            'preset_business': {
                'zh': '请准确转录商务会议内容，注意项目名称、公司名称、财务数据等关键信息的准确性。',
                'en': 'Accurately transcribe business meetings. Focus on project names, company names, financial data.'
            },
            'preset_medical': {
                'zh': '请准确转录医疗相关内容，特别注意症状描述、药品名称、医疗术语的准确性。',
                'en': 'Accurately transcribe medical content. Focus on symptoms, medication names, medical terms.'
            },

            # 预设热词
            'hotwords_ai': ['OpenAI', 'ChatGPT', '人工智能', '实时转录', '大语言模型', '机器学习', '深度学习'],
            'hotwords_tech': ['API', 'Python', '数据库', '服务器', '算法', '编程', '框架', '云计算'],
            'hotwords_business': ['项目', '会议', '客户', '方案', '预算', '合作', '营销', '战略'],
            'hotwords_medical': ['症状', '诊断', '治疗', '药物', '手术', '康复', '预防', '检查'],
            'hotwords_education': ['课程', '学习', '教学', '考试', '研究', '论文', '实验', '知识'],

            # 单位文本
            'unit_ms': {
                'zh': 'ms',
                'en': 'ms'
            },
            'unit_seconds': {
                'zh': '秒',
                'en': 's'
            },
            'unit_times': {
                'zh': '次',
                'en': 'times'
            },
            'unit_sentences': {
                'zh': '句',
                'en': 'sent'
            },
            'unit_chars_per_min': {
                'zh': '字/分',
                'en': 'cpm'
            },
            'unit_ms_per_char': {
                'zh': 'ms/字符',
                'en': 'ms/char'
            },
            'unit_percent': {
                'zh': '%',
                'en': '%'
            },
            'unit_pt': {
                'zh': 'pt',
                'en': 'pt'
            }
        }

    def get_text(self, key, default=None):
        """获取当前语言的文本"""
        try:
            text_dict = self.texts.get(key, {})
            return text_dict.get(self.current_language, default or key)
        except Exception as e:
            logger.error(f"获取文本失败: {key}, {e}")
            return default or key

    def set_language(self, language):
        """设置当前语言"""
        if language in self.languages:
            self.current_language = language
            return True
        return False

    def get_language_name(self, language):
        """获取语言显示名称"""
        return self.languages.get(language, language)


class SafeQueue:
    """线程安全的队列包装器"""

    def __init__(self, maxsize=0):
        self._queue = queue.Queue(maxsize=maxsize)
        self._mutex = QMutex()

    def put(self, item, timeout=None):
        with QMutexLocker(self._mutex):
            try:
                if timeout:
                    self._queue.put(item, timeout=timeout)
                else:
                    self._queue.put_nowait(item)
                return True
            except queue.Full:
                return False

    def get(self, timeout=None):
        with QMutexLocker(self._mutex):
            try:
                if timeout:
                    return self._queue.get(timeout=timeout)
                else:
                    return self._queue.get_nowait()
            except queue.Empty:
                return None

    def size(self):
        with QMutexLocker(self._mutex):
            return self._queue.qsize()

    def empty(self):
        with QMutexLocker(self._mutex):
            return self._queue.empty()


class CompactAudioVisualizer(QWidget):
    """紧凑型音频波形可视化组件"""

    def __init__(self):
        super().__init__()
        self.setMinimumHeight(80)
        self.setMaximumHeight(100)

        self.audio_buffer = deque(maxlen=600)
        self.sample_rate = 16000
        self.is_recording = False
        self._mutex = QMutex()

        # 优化的配色方案
        self.wave_color = QColor(0, 255, 127)
        self.wave_glow_color = QColor(0, 255, 127, 40)
        self.background_color = QColor(15, 15, 15)
        self.grid_color = QColor(35, 35, 35)

        if HAS_PYQTGRAPH:
            self._init_pyqtgraph()
        else:
            self._init_custom_paint()

        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(16)  # 60fps

    def _init_pyqtgraph(self):
        """初始化PyQtGraph波形显示"""
        try:
            layout = QVBoxLayout()
            layout.setContentsMargins(2, 2, 2, 2)

            self.plot_widget = pg.PlotWidget()
            self.plot_widget.setBackground((15, 15, 15))
            self.plot_widget.setLabel('left', '音量', color='#00FF7F', size='10pt')
            self.plot_widget.setLabel('bottom', '时间', color='#00FF7F', size='10pt')
            self.plot_widget.showGrid(x=True, y=True, alpha=0.15)
            self.plot_widget.setYRange(-1, 1)
            self.plot_widget.getAxis('left').setWidth(35)
            self.plot_widget.getAxis('bottom').setHeight(25)

            self.wave_curve = self.plot_widget.plot(
                pen=pg.mkPen(color=(0, 255, 127), width=1.5)
            )
            self.wave_glow = self.plot_widget.plot(
                pen=pg.mkPen(color=(0, 255, 127, 40), width=4)
            )

            layout.addWidget(self.plot_widget)
            self.setLayout(layout)
        except Exception as e:
            logger.error(f"PyQtGraph初始化失败: {e}")
            self._init_custom_paint()

    def _init_custom_paint(self):
        """初始化自定义绘制"""
        self.wave_points = []
        self.max_points = 150

    def add_audio_data(self, audio_data):
        """添加音频数据 - 线程安全"""
        try:
            with QMutexLocker(self._mutex):
                if isinstance(audio_data, bytes):
                    audio_array = np.frombuffer(audio_data, dtype=np.int16)
                    if len(audio_array) > 0:
                        audio_array = audio_array.astype(np.float32) / 32768.0
                        # 更敏感的音频检测，减少噪音
                        audio_array = np.where(np.abs(audio_array) > 0.001, audio_array, 0)
                        self.audio_buffer.extend(audio_array)
        except Exception as e:
            logger.error(f"添加音频数据失败: {e}")

    def update_display(self):
        """更新显示"""
        try:
            if not self.is_recording or len(self.audio_buffer) == 0:
                return

            if HAS_PYQTGRAPH:
                self._update_pyqtgraph()
            else:
                self._update_custom_paint()
        except Exception as e:
            logger.error(f"更新音频显示失败: {e}")

    def _update_pyqtgraph(self):
        """更新PyQtGraph显示"""
        try:
            with QMutexLocker(self._mutex):
                if len(self.audio_buffer) > 0:
                    data = list(self.audio_buffer)[-400:]
                    if len(data) > 0:
                        x = np.linspace(0, len(data) / self.sample_rate, len(data))
                        self.wave_curve.setData(x, data)
                        self.wave_glow.setData(x, data)
                        self.plot_widget.setXRange(0, len(data) / self.sample_rate)
        except Exception as e:
            logger.error(f"PyQtGraph更新失败: {e}")

    def _update_custom_paint(self):
        """更新自定义绘制"""
        try:
            with QMutexLocker(self._mutex):
                if len(self.audio_buffer) > 0:
                    recent_data = list(self.audio_buffer)[-self.max_points:]
                    self.wave_points = recent_data
                    self.update()
        except Exception as e:
            logger.error(f"自定义绘制更新失败: {e}")

    def paintEvent(self, event):
        """自定义绘制事件"""
        if HAS_PYQTGRAPH:
            return

        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)

            # 背景
            painter.fillRect(self.rect(), self.background_color)

            # 网格
            painter.setPen(QPen(self.grid_color, 1))
            width = self.width()
            height = self.height()

            for i in range(2):
                y = height * i
                painter.drawLine(0, y, width, y)

            # 波形
            if self.wave_points and len(self.wave_points) > 1:
                center_y = height / 2
                scale = height / 3

                # 发光效果
                painter.setPen(QPen(self.wave_glow_color, 6))
                self._draw_wave(painter, width, center_y, scale)

                # 主波形
                painter.setPen(QPen(self.wave_color, 2))
                self._draw_wave(painter, width, center_y, scale)
        except Exception as e:
            logger.error(f"绘制波形失败: {e}")

    def _draw_wave(self, painter, width, center_y, scale):
        """绘制波形"""
        try:
            for i in range(len(self.wave_points) - 1):
                x1 = width * i / len(self.wave_points)
                y1 = center_y - self.wave_points[i] * scale
                x2 = width * (i + 1) / len(self.wave_points)
                y2 = center_y - self.wave_points[i + 1] * scale
                painter.drawLine(int(x1), int(y1), int(x2), int(y2))
        except Exception as e:
            logger.error(f"绘制波形线条失败: {e}")

    def start_recording(self):
        """开始录音可视化"""
        self.is_recording = True
        with QMutexLocker(self._mutex):
            self.audio_buffer.clear()

    def stop_recording(self):
        """停止录音可视化"""
        self.is_recording = False
        try:
            if HAS_PYQTGRAPH and hasattr(self, 'wave_curve'):
                self.wave_curve.clear()
                self.wave_glow.clear()
            else:
                self.wave_points.clear()
                self.update()
        except Exception as e:
            logger.error(f"停止录音可视化失败: {e}")


class CompactVolumeIndicator(QWidget):
    """紧凑型音量指示器"""

    def __init__(self):
        super().__init__()
        self.setFixedSize(20, 80)
        self.volume_level = 0.0
        self.peak_level = 0.0
        self.peak_hold_time = 0
        self._mutex = QMutex()

        # 配色
        self.low_color = QColor(0, 255, 127)
        self.mid_color = QColor(255, 191, 0)
        self.high_color = QColor(255, 69, 0)
        self.background_color = QColor(20, 20, 20)
        self.border_color = QColor(60, 60, 60)

        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_peak)
        self.update_timer.start(40)

    def set_volume(self, level):
        """设置音量级别 - 线程安全"""
        try:
            with QMutexLocker(self._mutex):
                self.volume_level = max(0.0, min(1.0, level))
                if self.volume_level > self.peak_level:
                    self.peak_level = self.volume_level
                    self.peak_hold_time = 15
                self.update()
        except Exception as e:
            logger.error(f"设置音量级别失败: {e}")

    def update_peak(self):
        """更新峰值显示"""
        try:
            with QMutexLocker(self._mutex):
                if self.peak_hold_time > 0:
                    self.peak_hold_time -= 1
                else:
                    self.peak_level = max(0.0, self.peak_level - 0.03)
                    if self.peak_level < self.volume_level:
                        self.peak_level = self.volume_level
        except Exception as e:
            logger.error(f"更新峰值显示失败: {e}")

    def paintEvent(self, event):
        """绘制音量指示器"""
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)

            width = self.width()
            height = self.height()

            # 背景
            painter.fillRect(self.rect(), self.background_color)
            painter.setPen(QPen(self.border_color, 1))
            painter.drawRoundedRect(self.rect(), 3, 3)

            with QMutexLocker(self._mutex):
                if self.volume_level > 0:
                    volume_height = int(height * self.volume_level)
                    gradient = QLinearGradient(0, height, 0, 0)

                    if self.volume_level < 0.3:
                        gradient.setColorAt(0, self.low_color)
                        gradient.setColorAt(1, self.low_color)
                    elif self.volume_level < 0.7:
                        gradient.setColorAt(0, self.low_color)
                        gradient.setColorAt(0.5, self.mid_color)
                        gradient.setColorAt(1, self.mid_color)
                    else:
                        gradient.setColorAt(0, self.low_color)
                        gradient.setColorAt(0.4, self.mid_color)
                        gradient.setColorAt(0.8, self.high_color)
                        gradient.setColorAt(1, self.high_color)

                    painter.fillRect(1, height - volume_height, width - 2, volume_height,
                                     QBrush(gradient))

                # 峰值线
                if self.peak_level > 0:
                    peak_y = int(height * (1 - self.peak_level))
                    painter.setPen(QPen(QColor(255, 255, 255), 1))
                    painter.drawLine(1, peak_y, width - 1, peak_y)
        except Exception as e:
            logger.error(f"绘制音量指示器失败: {e}")


class NetworkMonitor(QThread):
    """网络状态监控器"""

    network_status_changed = pyqtSignal(bool, str)  # is_connected, status_message

    def __init__(self):
        super().__init__()
        self.running = False
        self.test_url = "https://api.openai.com"

    def run(self):
        self.running = True
        while self.running:
            try:
                response = requests.get(self.test_url, timeout=5)
                if response.status_code == 200:
                    self.network_status_changed.emit(True, "网络连接正常")
                else:
                    self.network_status_changed.emit(False, f"网络异常: {response.status_code}")
            except requests.RequestException as e:
                self.network_status_changed.emit(False, f"网络错误: {str(e)[:50]}")
            except Exception as e:
                self.network_status_changed.emit(False, f"未知错误: {str(e)[:50]}")

            time.sleep(10)  # 每10秒检查一次

    def stop(self):
        self.running = False


class AudioFileSplitter:
    """音频文件分割器"""

    @staticmethod
    def split_audio_file(file_path, max_size_mb=25):
        """分割音频文件"""
        if not HAS_PYDUB:
            raise ImportError("需要安装pydub: pip install pydub")

        try:
            file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
            if file_size <= max_size_mb:
                return [file_path]

            # 加载音频文件
            audio = AudioSegment.from_file(file_path)

            # 计算需要分割的段数
            duration_ms = len(audio)
            split_duration_ms = int((duration_ms * max_size_mb) / file_size)

            # 分割文件
            chunks = []
            chunk_files = []

            for i in range(0, duration_ms, split_duration_ms):
                chunk = audio[i:i + split_duration_ms]
                chunks.append(chunk)

            # 保存分割文件
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            temp_dir = tempfile.mkdtemp()

            for i, chunk in enumerate(chunks):
                chunk_file = os.path.join(temp_dir, f"{base_name}_part_{i + 1}.wav")
                chunk.export(chunk_file, format="wav")
                chunk_files.append(chunk_file)

            return chunk_files

        except Exception as e:
            logger.error(f"音频文件分割失败: {e}")
            raise


class UltraFastAudioRecorder:
    """超快速音频录制器 - 优化稳定性和准确度"""

    def __init__(self, config):
        self.chunk = 512  # 增加块大小，提高稳定性
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000
        self.audio = None
        self.stream = None

        # 音频处理参数 - 优化准确度
        self.silence_threshold = config.get('silence_threshold', 0.001)  # 提高阈值
        self.min_audio_length = config.get('min_audio_length', 0.02)
        self.noise_gate_enabled = config.get('noise_gate_enabled', True)

        self.audio_visualizer = None
        self.volume_indicator = None
        self.audio_queue = SafeQueue(maxsize=200)
        self.is_recording = False
        self.total_audio_bytes = 0
        self.last_audio_time = time.time()

        # 稳定性参数
        self.send_interval = 0.05  # 50ms发送一次，提高稳定性
        self.min_send_bytes = 320  # 最小发送字节数
        self.max_buffer_time = 0.1  # 100ms最大缓冲

        # 音频质量增强
        self.audio_filter_enabled = config.get('audio_filter_enabled', True)
        self.noise_reduction_level = config.get('noise_reduction_level', 0.3)

    def initialize_audio(self):
        """初始化音频系统"""
        try:
            if self.audio is None:
                self.audio = pyaudio.PyAudio()
            return True
        except Exception as e:
            logger.error(f"初始化音频系统失败: {e}")
            return False

    def set_visualizers(self, audio_visualizer, volume_indicator):
        """设置可视化组件"""
        self.audio_visualizer = audio_visualizer
        self.volume_indicator = volume_indicator

    def get_available_devices(self):
        """获取可用的音频输入设备"""
        devices = []
        try:
            if not self.initialize_audio():
                return devices

            for i in range(self.audio.get_device_count()):
                device_info = self.audio.get_device_info_by_index(i)
                if device_info['maxInputChannels'] > 0:
                    devices.append({
                        'index': i,
                        'name': device_info['name'],
                        'channels': device_info['maxInputChannels'],
                        'sample_rate': device_info['defaultSampleRate']
                    })
        except Exception as e:
            logger.error(f"获取设备信息失败: {e}")
        return devices

    def _apply_audio_filters(self, audio_data):
        """应用音频滤波器提高质量"""
        try:
            if not self.audio_filter_enabled:
                return audio_data

            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            if len(audio_array) == 0:
                return audio_data

            audio_float = audio_array.astype(np.float32)

            # 噪音门限
            if self.noise_gate_enabled:
                rms = np.sqrt(np.mean(audio_float ** 2))
                if rms < self.silence_threshold * 32768:
                    audio_float *= 0.1  # 大幅降低音量而不是完全静音

            # 简单的噪音抑制
            if self.noise_reduction_level > 0:
                # 简单的高通滤波器效果
                audio_float = audio_float * (1 - self.noise_reduction_level * 0.3)

            # 转换回int16
            audio_filtered = np.clip(audio_float, -32767, 32767).astype(np.int16)
            return audio_filtered.tobytes()

        except Exception as e:
            logger.error(f"音频滤波器处理失败: {e}")
            return audio_data

    def start_continuous_recording(self, device_index=None):
        """开始连续录音"""
        try:
            if not self.initialize_audio():
                return False

            if device_index is None:
                device_index = self._get_default_device()

            logger.info(f"使用录音设备: {device_index}")

            self.stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                frames_per_buffer=self.chunk,
                input_device_index=device_index,
                stream_callback=self._audio_callback
            )

            self.is_recording = True
            self.stream.start_stream()

            logger.info(f"音频录制启动成功 - 块大小: {self.chunk}")
            return True

        except Exception as e:
            logger.error(f"启动录音失败: {e}")
            return False

    def _audio_callback(self, in_data, frame_count, time_info, status):
        """音频回调函数 - 优化稳定性"""
        try:
            if status:
                logger.warning(f"音频回调状态警告: {status}")

            self.last_audio_time = time.time()

            # 应用音频滤波器
            filtered_data = self._apply_audio_filters(in_data)

            # 安全地添加到队列
            if self.audio_queue.put(filtered_data, timeout=0.001):
                self.total_audio_bytes += len(filtered_data)
            else:
                # 队列满时，清理一些旧数据
                for _ in range(10):
                    if self.audio_queue.get():
                        break

            # 可视化更新
            try:
                if self.audio_visualizer and self.is_recording:
                    self.audio_visualizer.add_audio_data(filtered_data)

                if self.volume_indicator and self.is_recording:
                    audio_array = np.frombuffer(filtered_data, dtype=np.int16)
                    if len(audio_array) > 0:
                        rms = np.sqrt(np.mean(audio_array.astype(np.float32) ** 2))
                        peak = np.max(np.abs(audio_array.astype(np.float32)))
                        audio_level = min(1.0, max(rms / 2000.0, peak / 32768.0))
                        self.volume_indicator.set_volume(audio_level)
            except Exception as e:
                logger.error(f"可视化更新失败: {e}")

        except Exception as e:
            logger.error(f"音频回调错误: {e}")

        return (None, pyaudio.paContinue)

    def get_audio_chunk_safe(self, timeout=0.01):
        """安全获取音频数据"""
        audio_chunks = []
        try:
            # 获取可用数据，但限制数量避免延迟
            max_chunks = 50
            for _ in range(max_chunks):
                chunk = self.audio_queue.get(timeout=timeout)
                if chunk is None:
                    break
                audio_chunks.append(chunk)

            if audio_chunks:
                return b''.join(audio_chunks)
            return None

        except Exception as e:
            logger.error(f"获取音频数据失败: {e}")
            return None

    def stop_recording(self):
        """停止录音"""
        try:
            self.is_recording = False
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None
            logger.info(f"录音已停止 - 总计: {self.total_audio_bytes} 字节")
        except Exception as e:
            logger.error(f"停止录音失败: {e}")

    def _get_default_device(self):
        """获取默认输入设备"""
        try:
            if not self.audio:
                return None
            default_device = self.audio.get_default_input_device_info()
            return default_device['index']
        except Exception as e:
            logger.error(f"获取默认设备失败: {e}")
            devices = self.get_available_devices()
            return devices[0]['index'] if devices else None

    def close(self):
        """关闭录音器"""
        try:
            self.stop_recording()
            if self.audio:
                self.audio.terminate()
                self.audio = None
        except Exception as e:
            logger.error(f"关闭录音器失败: {e}")


class TypewriterASRManager:
    """打字机式ASR管理器 - 优化换行控制"""

    def __init__(self):
        self.active_items = {}
        self.item_order = []
        self.character_queue = SafeQueue()
        self.completed_items_count = 0
        self.line_break_interval = 7  # 7次转录后换行

    def handle_committed(self, data):
        """处理committed事件"""
        item_id = data.get('item_id')
        previous_item_id = data.get('previous_item_id')

        if item_id:
            self.active_items[item_id] = {
                'id': item_id,
                'previous_id': previous_item_id,
                'transcription': '',
                'displayed_length': 0,
                'is_final': False,
                'start_time': time.time(),
                'last_update': time.time()
            }

            if previous_item_id and previous_item_id in self.active_items:
                try:
                    prev_index = self.item_order.index(previous_item_id)
                    self.item_order.insert(prev_index + 1, item_id)
                except ValueError:
                    self.item_order.append(item_id)
            else:
                self.item_order.append(item_id)

        return {
            'type': 'committed',
            'item_id': item_id,
            'previous_item_id': previous_item_id
        }

    def handle_transcription_delta(self, data):
        """处理转录增量"""
        item_id = data.get('item_id')
        delta = data.get('delta', '')

        if item_id in self.active_items:
            item = self.active_items[item_id]
            item['transcription'] += delta
            item['last_update'] = time.time()

            # 为打字机效果准备字符
            for char in delta:
                self.character_queue.put((item_id, char))

            return {
                'type': 'typewriter_delta',
                'item_id': item_id,
                'delta': delta,
                'full_text': item['transcription'],
                'displayed_length': item['displayed_length'],
                'new_chars_count': len(delta)
            }

        return None

    def get_next_character(self):
        """获取下一个要显示的字符"""
        return self.character_queue.get()

    def handle_transcription_completed(self, data):
        """处理转录完成"""
        item_id = data.get('item_id')
        final_transcript = data.get('transcript', '')

        if item_id in self.active_items:
            old_text = self.active_items[item_id]['transcription']
            self.active_items[item_id]['transcription'] = final_transcript
            self.active_items[item_id]['is_final'] = True

            self.completed_items_count += 1
            should_break_line = (self.completed_items_count % self.line_break_interval == 0)

            return {
                'type': 'typewriter_completed',
                'item_id': item_id,
                'final_text': final_transcript,
                'previous_text': old_text,
                'should_break_line': should_break_line
            }

        return None

    def mark_character_displayed(self, item_id):
        """标记字符已显示"""
        if item_id in self.active_items:
            self.active_items[item_id]['displayed_length'] += 1

    def cleanup_final_items(self, keep_recent=3):
        """清理已完成的项目"""
        try:
            final_items = [item_id for item_id in self.item_order
                           if item_id in self.active_items and self.active_items[item_id]['is_final']]

            if len(final_items) > keep_recent:
                items_to_remove = final_items[:-keep_recent]
                for item_id in items_to_remove:
                    if item_id in self.active_items:
                        del self.active_items[item_id]
                    if item_id in self.item_order:
                        self.item_order.remove(item_id)
        except Exception as e:
            logger.error(f"清理完成项目失败: {e}")


class UltraRealtimeTranscriber(QThread):
    """实时转录器 - 增强稳定性和网络处理"""

    # 信号
    typewriter_delta = pyqtSignal(str, str, str, int, int)
    typewriter_completed = pyqtSignal(str, str, str, bool)  # 添加should_break_line参数
    speech_committed = pyqtSignal(str, str)
    error_occurred = pyqtSignal(str)
    status_update = pyqtSignal(str, str)
    connection_status = pyqtSignal(str, str)

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.running = False
        self.recorder = UltraFastAudioRecorder(config)
        self.ws = None
        self.session_id = None
        self.is_connected = False
        self.connection_stable = False
        self.is_stopping = False

        # 打字机ASR管理器
        self.asr_manager = TypewriterASRManager()

        # 网络和超时管理
        self.connection_timeout = 10
        self.ping_interval = 8
        self.max_reconnect_attempts = 5
        self.reconnect_attempts = 0
        self.network_monitor = NetworkMonitor()

        # 统计
        self.audio_chunks_sent = 0
        self.messages_received = 0
        self.transcription_start_time = None
        self.last_successful_send = time.time()

    def set_visualizers(self, audio_visualizer, volume_indicator):
        """设置音频可视化组件"""
        self.recorder.set_visualizers(audio_visualizer, volume_indicator)

    def run(self):
        """主转录循环 - 增强异常处理"""
        self.running = True
        self.is_stopping = False
        self.transcription_start_time = time.time()

        # 启动网络监控
        self.network_monitor.network_status_changed.connect(self._handle_network_status)
        self.network_monitor.start()

        while self.running and not self.is_stopping and self.reconnect_attempts < self.max_reconnect_attempts:
            try:
                self._establish_connection()
                if self.is_connected:
                    self.reconnect_attempts = 0
                    break
            except Exception as e:
                if not self.is_stopping:
                    self.reconnect_attempts += 1
                    error_msg = f"连接失败 (尝试 {self.reconnect_attempts}/{self.max_reconnect_attempts}): {str(e)}"
                    self.error_occurred.emit(error_msg)
                    logger.error(error_msg)

                    if self.reconnect_attempts < self.max_reconnect_attempts:
                        wait_time = min(2 ** self.reconnect_attempts, 8)
                        time.sleep(wait_time)

        if not self.is_connected and not self.is_stopping:
            self.error_occurred.emit("无法建立连接，已达到最大重试次数")

        # 停止网络监控
        if self.network_monitor.isRunning():
            self.network_monitor.stop()
            self.network_monitor.wait(2000)

    def _handle_network_status(self, is_connected, status_message):
        """处理网络状态变化"""
        if not is_connected and self.is_connected:
            logger.warning(f"网络连接异常: {status_message}")
            # 可以在这里触发重连逻辑

    def _establish_connection(self):
        """建立WebSocket连接 - 修复超时参数问题"""
        if self.is_stopping:
            return

        try:
            base_url = self.config.get('base_url', 'https://api.openai.com/v1')
            ws_url = base_url.replace('https://', 'wss://').replace('http://', 'ws://')
            if not ws_url.endswith('/v1'):
                ws_url = ws_url.rstrip('/') + '/v1'
            ws_url += "/realtime?intent=transcription"

            logger.info(f"连接实时ASR: {ws_url}")
            self.connection_status.emit("🔄 建立连接...", "#FFD700")

            self.ws = websocket.WebSocketApp(
                ws_url,
                header={
                    "Authorization": f"Bearer {self.config['api_key']}",
                    "OpenAI-Beta": "realtime=v1"
                },
                on_open=self.on_open,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close
            )

            # 移除不支持的timeout参数，只保留ping相关参数
            self.ws.run_forever(
                ping_interval=self.ping_interval,
                ping_timeout=5
            )

        except Exception as e:
            if not self.is_stopping:
                error_msg = f"建立连接失败: {str(e)}"
                self.error_occurred.emit(error_msg)
                logger.error(error_msg)
                raise

    def on_open(self, ws):
        """WebSocket连接建立"""
        if self.is_stopping:
            return

        try:
            logger.info("✅ 实时ASR连接已建立")
            self.is_connected = True
            self.connection_status.emit("⚡ 已连接", "#00FF7F")

            self._send_optimized_config()
            self._start_audio_pipeline()
        except Exception as e:
            logger.error(f"连接建立后初始化失败: {e}")
            self.error_occurred.emit(f"初始化失败: {str(e)}")

    def _send_optimized_config(self):
        """发送优化的配置 - 修复提示词问题"""
        try:
            # 构建简化的提示词，避免内容泄露
            optimized_prompt = self._build_optimized_prompt()

            config_message = {
                "type": "transcription_session.update",
                "session": {
                    "input_audio_format": "pcm16",
                    "input_audio_transcription": {
                        "model": self.config.get('model', 'gpt-4o-transcribe'),
                    },
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": self.config.get('vad_threshold', 0.15),
                        "prefix_padding_ms": 200,
                        "silence_duration_ms": self.config.get('silence_duration_ms', 300)
                    },
                    "input_audio_noise_reduction": {
                        "type": "near_field"
                    }
                }
            }

            # 语言配置
            if self.config.get('language') and self.config['language'] != 'auto':
                config_message["session"]["input_audio_transcription"]["language"] = self.config['language']

            # 只在提示词简短且安全时才设置
            if optimized_prompt and len(optimized_prompt) < 100:
                config_message["session"]["input_audio_transcription"]["prompt"] = optimized_prompt
                logger.info(f"设置提示词: {optimized_prompt}")
            else:
                logger.info("跳过提示词设置，使用默认配置")

            logger.info("发送优化配置")
            if self.ws and self.is_connected:
                self.ws.send(json.dumps(config_message))

        except Exception as e:
            logger.error(f"发送配置失败: {e}")
            self.error_occurred.emit(f"配置失败: {str(e)}")

    def _build_optimized_prompt(self):
        """构建优化的提示词 - 修复内容泄露问题"""
        language = self.config.get('language', 'zh')
        base_prompt = self.config.get('prompt', '')
        hotwords = self.config.get('hotwords', [])

        # 简化的语言特定指令 - 避免被误解为输出内容
        language_instructions = {
            'zh': "转录中文语音，保持准确流畅。",
            'en': "Transcribe English speech accurately and fluently.",
            'ja': "日本語音声を正確に転写。",
            'ko': "한국어 음성을 정확히 전사.",
            'fr': "Transcrire la parole française avec précision.",
            'de': "Deutsche Sprache genau transkribieren.",
            'es': "Transcribir español con precisión.",
            'it': "Trascrivere italiano accuratamente.",
            'pt': "Transcrever português com precisão.",
            'ru': "Точно транскрибировать русскую речь.",
            'ar': "نسخ الكلام العربي بدقة.",
            'hi': "हिंदी भाषण को सटीक रूप से ट्रांसक्राइब करें।"
        }

        # 使用简洁的基础指令
        instruction = language_instructions.get(language, language_instructions['zh'])

        # 避免使用可能被误解的复杂提示词
        optimized_prompt = instruction

        # 简化热词处理 - 只添加最重要的词汇
        if hotwords:
            # 只取前8个最重要的热词，避免提示词过长
            important_hotwords = hotwords[:8]
            if important_hotwords:
                hotwords_str = ', '.join(important_hotwords)
                # 使用简单格式，避免被误解
                optimized_prompt += f" 重点词汇: {hotwords_str}."

        # 不再添加复杂的base_prompt，避免内容泄露
        # 如果用户确实需要自定义提示词，进行严格过滤
        if base_prompt and len(base_prompt.strip()) < 50:  # 限制长度
            # 过滤可能被误解的内容
            filtered_prompt = base_prompt.replace("请提供", "").replace("输出", "").replace("显示", "")
            if filtered_prompt.strip():
                optimized_prompt += f" {filtered_prompt.strip()}"

        return optimized_prompt

    def _start_audio_pipeline(self):
        """启动音频管道 - 优化稳定性"""

        def safe_audio_sender():
            device_index = self.config.get('device_index')
            if not self.recorder.start_continuous_recording(device_index):
                if not self.is_stopping:
                    self.error_occurred.emit("启动录音失败")
                return

            self.status_update.emit("⚡ 音频管道启动", "#00FF7F")
            logger.info("🚀 音频管道启动...")

            audio_buffer = b''
            chunk_size = 640  # 40ms @ 16kHz，平衡质量和延迟
            min_send_size = 320
            max_buffer_time = 0.08
            force_send_interval = 0.15

            last_send_time = time.time()
            consecutive_failures = 0
            max_consecutive_failures = 5

            while self.running and not self.is_stopping and self.is_connected:
                try:
                    current_time = time.time()
                    audio_data = self.recorder.get_audio_chunk_safe(timeout=0.005)

                    if audio_data and len(audio_data) > 0:
                        audio_buffer += audio_data

                    time_since_last_send = current_time - last_send_time

                    # 发送条件
                    should_send = (
                            len(audio_buffer) >= chunk_size or
                            (len(audio_buffer) >= min_send_size and time_since_last_send >= max_buffer_time) or
                            time_since_last_send >= force_send_interval
                    )

                    if should_send and len(audio_buffer) > 0:
                        if self._send_audio_chunk_safe(audio_buffer):
                            audio_buffer = b''
                            last_send_time = current_time
                            consecutive_failures = 0
                            self.last_successful_send = current_time
                        else:
                            consecutive_failures += 1
                            if consecutive_failures >= max_consecutive_failures:
                                logger.error("连续发送失败次数过多，停止发送")
                                break

                    time.sleep(0.001)  # 1ms睡眠

                except Exception as e:
                    if not self.is_stopping:
                        logger.error(f"音频发送错误: {e}")
                        consecutive_failures += 1
                        if consecutive_failures >= max_consecutive_failures:
                            break
                        time.sleep(0.01)

            logger.info("🔇 音频管道结束")

        audio_thread = threading.Thread(target=safe_audio_sender, daemon=True)
        audio_thread.start()

    def _send_audio_chunk_safe(self, audio_data):
        """安全发送音频块"""
        try:
            if self.is_stopping or not self.is_connected or not self.ws:
                return False

            audio_b64 = base64.b64encode(audio_data).decode('utf-8')

            message = {
                "type": "input_audio_buffer.append",
                "audio": audio_b64
            }

            self.ws.send(json.dumps(message))
            self.audio_chunks_sent += 1

            if self.audio_chunks_sent % 100 == 0:
                logger.info(f"📊 已发送 {self.audio_chunks_sent} 个音频块")

            return True

        except Exception as e:
            if not self.is_stopping:
                logger.error(f"发送音频块失败: {e}")
            return False

    def on_message(self, ws, message):
        """处理WebSocket消息 - 增强异常处理"""
        if self.is_stopping:
            return

        try:
            data = json.loads(message)
            msg_type = data.get('type', '')
            self.messages_received += 1

            # 关键事件日志
            if msg_type in [
                'input_audio_buffer.committed',
                'conversation.item.input_audio_transcription.delta',
                'conversation.item.input_audio_transcription.completed',
                'error'
            ]:
                logger.debug(f"[{self.messages_received}] 事件: {msg_type}")

            if msg_type == 'transcription_session.created':
                self.session_id = data.get('session', {}).get('id')
                self.connection_stable = True
                logger.info(f"✅ ASR会话创建: {self.session_id}")

            elif msg_type == 'transcription_session.updated':
                logger.info("⚙️ ASR配置已更新")

            elif msg_type == 'input_audio_buffer.committed':
                self._handle_audio_committed(data)

            elif msg_type == 'conversation.item.input_audio_transcription.delta':
                self._handle_transcription_delta(data)

            elif msg_type == 'conversation.item.input_audio_transcription.completed':
                self._handle_transcription_completed(data)

            elif msg_type == 'input_audio_buffer.speech_started':
                self.status_update.emit("⚡ 检测到语音", "#00FF7F")

            elif msg_type == 'input_audio_buffer.speech_stopped':
                self.status_update.emit("⏸️ 语音结束", "#FFD700")

            elif msg_type == 'error':
                self._handle_api_error(data)

        except json.JSONDecodeError as e:
            if not self.is_stopping:
                logger.error(f"JSON解析错误: {e}")
        except Exception as e:
            if not self.is_stopping:
                logger.error(f"消息处理错误: {e}")

    def _handle_api_error(self, data):
        """处理API错误"""
        error_info = data.get('error', {})
        error_msg = error_info.get('message', '未知错误')
        error_code = error_info.get('code', '')
        error_type = error_info.get('type', '')

        full_error_msg = f"API错误 [{error_code}] {error_type}: {error_msg}"
        logger.error(full_error_msg)

        if not self.is_stopping:
            self.error_occurred.emit(full_error_msg)

    def _handle_audio_committed(self, data):
        """处理音频提交事件"""
        try:
            result = self.asr_manager.handle_committed(data)
            if result:
                logger.debug(f"⚡ 音频已提交: {result['item_id']}")
                self.speech_committed.emit(
                    result['item_id'],
                    result['previous_item_id'] or ''
                )
        except Exception as e:
            logger.error(f"处理音频提交失败: {e}")

    def _handle_transcription_delta(self, data):
        """处理转录增量 - 修复参数问题"""
        try:
            result = self.asr_manager.handle_transcription_delta(data)
            if result:
                # 过滤可能的提示词泄露内容
                filtered_delta = self._filter_prompt_leakage(result['delta'])

                if filtered_delta:
                    # 发射信号，传递所有必要的参数
                    self.typewriter_delta.emit(
                        result['item_id'],
                        filtered_delta,
                        result['full_text'],
                        result['displayed_length'],
                        result['new_chars_count']
                    )

                    logger.debug(f"⚡ 增量 [{result['item_id']}]: '{filtered_delta}'")
        except Exception as e:
            logger.error(f"处理转录增量失败: {e}")

    def _handle_transcription_completed(self, data):
        """处理转录完成 - 修复参数问题"""
        try:
            result = self.asr_manager.handle_transcription_completed(data)
            if result:
                # 过滤可能的提示词泄露内容
                filtered_text = self._filter_prompt_leakage(result['final_text'])

                if filtered_text:
                    # 发射信号，传递所有必要的参数
                    self.typewriter_completed.emit(
                        result['item_id'],
                        filtered_text,
                        result['previous_text'],
                        result['should_break_line']
                    )

                    logger.debug(
                        f"✅ 完成 [{result['item_id']}]: '{filtered_text}' (换行: {result['should_break_line']})")
        except Exception as e:
            logger.error(f"处理转录完成失败: {e}")

    def _filter_prompt_leakage(self, text):
        """过滤提示词泄露内容"""
        try:
            if not text:
                return text

            # 定义可能泄露的提示词片段
            prompt_keywords = [
                "转录中文语音", "保持准确流畅", "Transcribe English", "重点词汇",
                "転写", "전사", "Transcrire", "transkribieren", "Transcribir",
                "Trascrivere", "Transcrever", "транскрибировать", "نسخ", "ट्रांसक्राइब"
            ]

            # 过滤明显的提示词内容
            filtered_text = text
            for keyword in prompt_keywords:
                if keyword in filtered_text:
                    # 如果包含提示词关键字，可能是泄露，过滤掉
                    filtered_text = filtered_text.replace(keyword, "").strip()

            # 如果文本过短或全是提示词内容，返回空
            if len(filtered_text.strip()) < 2:
                return ""

            # 过滤以冒号结尾的可能是标签的内容
            if filtered_text.strip().endswith(":") and len(filtered_text.strip()) < 10:
                return ""

            return filtered_text

        except Exception as e:
            logger.error(f"过滤提示词泄露失败: {e}")
            return text

    def on_error(self, ws, error):
        """WebSocket错误处理"""
        if self.is_stopping:
            return

        self.is_connected = False
        self.connection_stable = False
        self.connection_status.emit("❌ 连接错误", "#FF4545")

        error_msg = f"WebSocket错误: {str(error)}"
        logger.error(error_msg)

        if not self.is_stopping:
            self.error_occurred.emit(error_msg)

    def on_close(self, ws, close_status_code, close_msg):
        """WebSocket连接关闭"""
        self.is_connected = False
        self.connection_stable = False

        if not self.is_stopping:
            self.connection_status.emit("🔌 连接断开", "#FFD700")

        self.recorder.stop_recording()
        logger.info(f"🔌 连接关闭: {close_status_code} - {close_msg}")
        logger.info(f"📊 会话统计：发送 {self.audio_chunks_sent} 音频块，收到 {self.messages_received} 消息")

    def stop_transcription(self):
        """停止转录"""
        logger.info("⏹️ 正在停止转录...")
        self.is_stopping = True
        self.running = False
        self.is_connected = False

        try:
            self.recorder.stop_recording()

            if self.ws:
                self.ws.close()
                self.ws = None

            if self.network_monitor.isRunning():
                self.network_monitor.stop()
                self.network_monitor.wait(2000)
        except Exception as e:
            logger.error(f"停止转录时出错: {e}")

        self.status_update.emit("⏹️ 已停止", "#FFD700")


class TypewriterDisplayWidget(QTextBrowser):
    """打字机效果实时显示组件 - 修复颜色转换问题"""

    def __init__(self):
        super().__init__()
        self.setFont(QFont("Microsoft YaHei", 18, QFont.Normal))

        # 打字机状态
        self.typewriter_items = {}
        self.display_order = []
        self.character_queue = SafeQueue()
        self.current_line_items = []  # 当前行的项目

        # 添加颜色转换锁，防止竞争条件
        self._conversion_mutex = QMutex()

        # 打字机定时器
        self.typewriter_timer = QTimer()
        self.typewriter_timer.timeout.connect(self._process_typewriter_queue)
        self.typewriter_timer.start(12)  # 12ms处理间隔

        # 样式
        self.streaming_style = """
            color: #FFD700; 
            background: rgba(255, 215, 0, 0.08); 
            padding: 4px 8px; 
            border-radius: 4px;
            border-left: 2px solid #FFD700;
            margin: 2px 0;
            font-family: 'Microsoft YaHei', sans-serif;
            line-height: 1.4;
            display: inline;
        """

        self.completed_style = """
            color: #00FF7F; 
            background: rgba(0, 255, 127, 0.08); 
            padding: 4px 8px; 
            border-radius: 4px;
            border-left: 2px solid #00FF7F;
            margin: 2px 0;
            font-family: 'Microsoft YaHei', sans-serif;
            line-height: 1.4;
            display: inline;
        """

        self.setStyleSheet("""
            QTextBrowser {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #0f0f0f, stop:1 #1a1a1a);
                color: #E0E0E0;
                border: 2px solid #00FF7F;
                border-radius: 10px;
                padding: 20px;
                selection-background-color: #00FF7F;
                selection-color: #000000;
                font-size: 18px;
                line-height: 1.8;
                letter-spacing: 0.3px;
            }
        """)

    def add_typewriter_text(self, item_id, delta_text, full_text, displayed_length, new_chars_count):
        """添加打字机文本"""
        try:
            with QMutexLocker(self._conversion_mutex):
                # 将新字符加入队列
                for char in delta_text:
                    self.character_queue.put((item_id, char))

                # 如果是新项目，创建占位符
                if item_id not in self.typewriter_items:
                    self._create_typewriter_item(item_id)
        except Exception as e:
            logger.error(f"添加打字机文本失败: {e}")

    def _create_typewriter_item(self, item_id):
        """创建打字机项目占位符"""
        try:
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.End)

            start_position = cursor.position()

            # 创建空的占位符，避免初始HTML冲突
            placeholder_html = f"""<span id='item_{item_id}' class='streaming'></span>"""
            cursor.insertHtml(placeholder_html)

            # 记录项目信息
            self.typewriter_items[item_id] = {
                'start_position': start_position,
                'end_position': cursor.position(),
                'text': '',
                'displayed_text': '',
                'is_typing': True,
                'is_finalizing': False  # 添加标志防止重复处理
            }

            if item_id not in self.display_order:
                self.display_order.append(item_id)
                self.current_line_items.append(item_id)

            self._auto_scroll()
        except Exception as e:
            logger.error(f"创建打字机项目失败: {e}")

    def _process_typewriter_queue(self):
        """处理打字机字符队列 - 修复处理逻辑"""
        try:
            # 限制处理字符数量，避免UI阻塞
            max_chars_per_cycle = 5
            processed_count = 0

            while processed_count < max_chars_per_cycle:
                char_data = self.character_queue.get()
                if char_data is None:
                    break

                item_id, char = char_data

                # 检查项目是否还在活跃状态
                if item_id in self.typewriter_items and not self.typewriter_items[item_id].get('is_finalizing', False):
                    self._add_character_to_item(item_id, char)
                    processed_count += 1
                else:
                    # 如果项目已经完成或不存在，跳过这个字符
                    continue

        except Exception as e:
            logger.error(f"打字机处理错误: {e}")

    def _add_character_to_item(self, item_id, char):
        """向项目添加字符 - 改进显示更新"""
        try:
            if item_id not in self.typewriter_items:
                self._create_typewriter_item(item_id)

            item_info = self.typewriter_items[item_id]

            # 如果正在完成中，不再添加字符
            if item_info.get('is_finalizing', False):
                return

            item_info['displayed_text'] += char

            # 批量更新显示，减少频繁的DOM操作
            if len(item_info['displayed_text']) % 3 == 0 or char in [' ', '，', '。', '！', '？', '.', '!', '?']:
                self._update_typewriter_display(item_id)
        except Exception as e:
            logger.error(f"添加字符失败: {e}")

    def _update_typewriter_display(self, item_id):
        """更新打字机显示 - 确保样式正确"""
        try:
            if item_id not in self.typewriter_items:
                return

            item_info = self.typewriter_items[item_id]

            # 如果正在完成中，不再更新
            if item_info.get('is_finalizing', False):
                return

            # 移动到项目位置
            cursor = self.textCursor()
            cursor.setPosition(item_info['start_position'])
            cursor.setPosition(item_info['end_position'], QTextCursor.KeepAnchor)

            # 转义特殊字符
            escaped_text = (item_info['displayed_text']
                            .replace('&', '&amp;')
                            .replace('<', '&lt;')
                            .replace('>', '&gt;')
                            .replace('"', '&quot;')
                            .replace("'", '&#39;'))

            # 确保使用统一的黄色流式样式
            streaming_html = f"""
            <span id='item_{item_id}' style='
                color: #FFD700 !important; 
                background: rgba(255, 215, 0, 0.1) !important; 
                padding: 2px 4px; 
                border-radius: 3px; 
                font-weight: 500;
                border-left: 2px solid #FFD700;
            '>{escaped_text}</span>
            """

            cursor.insertHtml(streaming_html)

            # 更新位置信息
            item_info['end_position'] = cursor.position()

            self._auto_scroll()
        except Exception as e:
            logger.error(f"更新打字机显示失败: {e}")

    def finalize_typewriter_item(self, item_id, final_text, previous_text, should_break_line=False):
        """完成打字机项目 - 强制转换为绿色并清理"""
        try:
            with QMutexLocker(self._conversion_mutex):
                # 如果项目不存在，直接添加为完成文本
                if item_id not in self.typewriter_items:
                    self._add_completed_text(item_id, final_text, should_break_line)
                    return

                # 标记为正在完成，防止继续添加字符
                self.typewriter_items[item_id]['is_finalizing'] = True

                # 清空该项目相关的队列字符
                self._clear_item_from_queue(item_id)

                item_info = self.typewriter_items[item_id]

                # 移动到项目位置并完全替换内容
                cursor = self.textCursor()
                cursor.setPosition(item_info['start_position'])
                cursor.setPosition(item_info['end_position'], QTextCursor.KeepAnchor)

                # 完全清除选中内容
                cursor.removeSelectedText()

                # 转义最终文本
                escaped_text = (final_text
                                .replace('&', '&amp;')
                                .replace('<', '&lt;')
                                .replace('>', '&gt;')
                                .replace('"', '&quot;')
                                .replace("'", '&#39;'))

                line_break = "<br>" if should_break_line else " "

                # 使用强制的绿色样式，确保完全覆盖黄色
                completed_html = f"""
                <span style='
                    color: #00FF7F !important; 
                    background: rgba(0, 255, 127, 0.1) !important; 
                    padding: 2px 4px; 
                    border-radius: 3px; 
                    font-weight: 500; 
                    border-left: 2px solid #00FF7F !important;
                '>{escaped_text}</span>{line_break}
                """

                cursor.insertHtml(completed_html)

                # 清除打字机项目记录
                del self.typewriter_items[item_id]
                if item_id in self.display_order:
                    self.display_order.remove(item_id)
                if item_id in self.current_line_items:
                    self.current_line_items.remove(item_id)

                # 如果需要换行，清空当前行项目列表
                if should_break_line:
                    self.current_line_items.clear()

                self._auto_scroll()

                logger.debug(f"✅ 成功完成项目 {item_id}，文本已转为绿色")

        except Exception as e:
            logger.error(f"完成打字机项目失败: {e}")
            # 如果出现异常，尝试强制清理
            try:
                if item_id in self.typewriter_items:
                    del self.typewriter_items[item_id]
            except:
                pass

    def _clear_item_from_queue(self, item_id):
        """从队列中清除指定项目的所有字符"""
        try:
            # 临时存储其他项目的字符
            temp_chars = []

            # 清空队列并过滤掉指定项目的字符
            while not self.character_queue.empty():
                char_data = self.character_queue.get()
                if char_data and char_data[0] != item_id:
                    temp_chars.append(char_data)

            # 将其他项目的字符重新加入队列
            for char_data in temp_chars:
                self.character_queue.put(char_data)

        except Exception as e:
            logger.error(f"清理队列失败: {e}")

    def _add_completed_text(self, item_id, final_text, should_break_line=False):
        """添加完成文本 - 直接绿色显示"""
        try:
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.End)

            line_break = "<br>" if should_break_line else " "
            escaped_text = (final_text
                            .replace('&', '&amp;')
                            .replace('<', '&lt;')
                            .replace('>', '&gt;')
                            .replace('"', '&quot;')
                            .replace("'", '&#39;'))

            # 直接使用绿色完成样式
            completed_html = f"""
            <span style='
                color: #00FF7F !important; 
                background: rgba(0, 255, 127, 0.1) !important; 
                padding: 2px 4px; 
                border-radius: 3px; 
                font-weight: 500; 
                border-left: 2px solid #00FF7F !important;
            '>{escaped_text}</span>{line_break}
            """

            cursor.insertHtml(completed_html)
            self._auto_scroll()
        except Exception as e:
            logger.error(f"添加完成文本失败: {e}")

    def _force_convert_all_to_green(self):
        """强制将所有黄色文本转换为绿色 - 清理函数"""
        try:
            # 获取所有文本内容
            html_content = self.toHtml()

            # 替换所有黄色样式为绿色
            html_content = html_content.replace('#FFD700', '#00FF7F')
            html_content = html_content.replace('255, 215, 0', '0, 255, 127')
            html_content = html_content.replace('rgba(255, 215, 0', 'rgba(0, 255, 127')

            # 重新设置内容
            self.setHtml(html_content)

            logger.debug("强制转换所有文本为绿色完成")
        except Exception as e:
            logger.error(f"强制转换颜色失败: {e}")

    def clear_all_typewriter(self):
        """清除所有打字机项目 - 确保完全清理"""
        try:
            # 首先停止定时器
            if hasattr(self, 'typewriter_timer'):
                self.typewriter_timer.stop()

            with QMutexLocker(self._conversion_mutex):
                # 强制转换所有未完成的文本为绿色
                self._force_convert_all_to_green()

                # 清理所有状态
                self.typewriter_items.clear()
                self.display_order.clear()
                self.current_line_items.clear()

                # 彻底清空字符队列
                queue_cleared = 0
                while not self.character_queue.empty() and queue_cleared < 1000:
                    if self.character_queue.get() is None:
                        break
                    queue_cleared += 1

            # 重新启动定时器
            if hasattr(self, 'typewriter_timer'):
                self.typewriter_timer.start(12)

        except Exception as e:
            logger.error(f"清除打字机项目失败: {e}")

    def _auto_scroll(self):
        """自动滚动到底部"""
        try:
            scrollbar = self.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
        except Exception as e:
            logger.error(f"自动滚动失败: {e}")


class FileTranscriptionWorker(QThread):
    """文件转录工作线程 - 支持大文件分割"""

    progress_update = pyqtSignal(int)
    transcription_ready = pyqtSignal(str, str, dict)
    error_occurred = pyqtSignal(str)
    status_update = pyqtSignal(str, str)

    def __init__(self, file_path, config, output_format='text'):
        super().__init__()
        self.file_path = file_path
        self.config = config
        self.output_format = output_format
        self.is_cancelled = False
        self.max_file_size_mb = 25

    def run(self):
        """执行文件转录"""
        try:
            self.status_update.emit("📁 正在处理文件...", "#FFD700")
            self.progress_update.emit(5)

            file_size_mb = os.path.getsize(self.file_path) / (1024 * 1024)
            logger.info(f"文件大小: {file_size_mb:.2f} MB")

            if file_size_mb > self.max_file_size_mb:
                self._handle_large_file()
            else:
                self.progress_update.emit(20)
                client = self._create_openai_client()
                self.progress_update.emit(40)
                self._transcribe_standard(client)

        except Exception as e:
            error_msg = f"文件转录失败: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)

    def _create_openai_client(self):
        """创建OpenAI客户端"""
        try:
            if self.config.get('base_url'):
                return openai.OpenAI(
                    api_key=self.config['api_key'],
                    base_url=self.config['base_url']
                )
            else:
                return openai.OpenAI(api_key=self.config['api_key'])
        except Exception as e:
            logger.error(f"创建OpenAI客户端失败: {e}")
            raise

    def _transcribe_standard(self, client):
        """标准转录文件"""
        try:
            self.status_update.emit("📝 开始转录...", "#00FF7F")

            with open(self.file_path, 'rb') as audio_file:
                params = {
                    "model": "whisper-1",
                    "file": audio_file,
                    "response_format": self.output_format
                }

                self._add_optional_params(params)
                self.progress_update.emit(70)

                if self.is_cancelled:
                    return

                response = client.audio.transcriptions.create(**params)
                self.progress_update.emit(90)

                text = response.text if hasattr(response, 'text') else str(response)

                if text and not self.is_cancelled:
                    timestamp = time.strftime("%H:%M:%S")
                    metadata = {
                        'source': 'file_standard',
                        'format': self.output_format,
                        'file_path': self.file_path,
                        'file_size': os.path.getsize(self.file_path)
                    }

                    self.transcription_ready.emit(text, timestamp, metadata)

                self.progress_update.emit(100)
                self.status_update.emit("✅ 转录完成", "#00FF7F")

        except Exception as e:
            error_msg = f"标准转录失败: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)

    def _handle_large_file(self):
        """处理大文件 - 分割转录"""
        try:
            self.status_update.emit("📋 正在分割大文件...", "#FFD700")

            if not HAS_PYDUB:
                self.error_occurred.emit("处理大文件需要安装 pydub: pip install pydub")
                return

            # 分割文件
            chunk_files = AudioFileSplitter.split_audio_file(self.file_path, self.max_file_size_mb)

            if self.is_cancelled:
                return

            self.progress_update.emit(30)

            # 转录各个分块
            client = self._create_openai_client()
            all_transcriptions = []

            total_chunks = len(chunk_files)

            for i, chunk_file in enumerate(chunk_files):
                if self.is_cancelled:
                    break

                self.status_update.emit(f"📝 转录第 {i + 1}/{total_chunks} 部分...", "#00FF7F")

                try:
                    with open(chunk_file, 'rb') as audio_file:
                        params = {
                            "model": "whisper-1",
                            "file": audio_file,
                            "response_format": self.output_format
                        }

                        self._add_optional_params(params)
                        response = client.audio.transcriptions.create(**params)

                        text = response.text if hasattr(response, 'text') else str(response)
                        if text:
                            all_transcriptions.append(text)

                        # 更新进度
                        progress = 30 + (i + 1) * 60 // total_chunks
                        self.progress_update.emit(progress)

                except Exception as e:
                    logger.error(f"转录分块 {i + 1} 失败: {e}")
                    all_transcriptions.append(f"[第{i + 1}部分转录失败: {str(e)}]")

                finally:
                    # 清理临时文件
                    try:
                        os.remove(chunk_file)
                    except:
                        pass

            if not self.is_cancelled and all_transcriptions:
                # 合并转录结果
                final_text = "\n".join(all_transcriptions)
                timestamp = time.strftime("%H:%M:%S")
                metadata = {
                    'source': 'file_large_split',
                    'format': self.output_format,
                    'file_path': self.file_path,
                    'file_size': os.path.getsize(self.file_path),
                    'chunks_count': total_chunks
                }

                self.transcription_ready.emit(final_text, timestamp, metadata)

            self.progress_update.emit(100)
            self.status_update.emit("✅ 大文件转录完成", "#00FF7F")

        except Exception as e:
            error_msg = f"大文件处理失败: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)

    def _add_optional_params(self, params):
        """添加可选参数"""
        try:
            if self.config.get('language') and self.config['language'] != 'auto':
                params["language"] = self.config['language']

            prompt = self._build_hotwords_prompt()
            if prompt:
                params["prompt"] = prompt
        except Exception as e:
            logger.error(f"添加可选参数失败: {e}")

    def _build_hotwords_prompt(self):
        """构建热词提示"""
        try:
            base_prompt = self.config.get('prompt', '')
            hotwords = self.config.get('hotwords', [])

            if hotwords:
                hotwords_str = ', '.join(hotwords[:30])
                hotwords_prompt = f"重要术语: {hotwords_str}"

                if base_prompt:
                    return f"{base_prompt}. {hotwords_prompt}"
                else:
                    return hotwords_prompt

            return base_prompt
        except Exception as e:
            logger.error(f"构建热词提示失败: {e}")
            return ""

    def cancel(self):
        """取消转录"""
        self.is_cancelled = True


class UltraRealtimeSubtitleApp(QMainWindow):
    """实时字幕应用 - 全面优化稳定性和功能，支持多语言界面"""

    def __init__(self):
        super().__init__()

        # 初始化配置管理器和语言管理器
        self.config_manager = ConfigManager()
        self.lang_manager = LanguageManager()

        # 加载保存的配置
        self.saved_config = self.config_manager.load_config()

        # 设置界面语言
        self.saved_lang = self.saved_config.get('ui_language', 'zh')
        self.lang_manager.set_language(self.saved_lang)

        self.transcription_thread = None
        self.file_transcription_worker = None
        self.subtitle_history = deque(maxlen=5000)
        self.current_config = self._get_default_config()
        self.audio_devices = []

        # 统计相关
        self.total_chars = 0
        self.session_start_time = None

        # 异常处理
        self.error_count = 0
        self.max_errors = 10

        # 设置异常处理器
        sys.excepthook = self._handle_exception

        # 设置暗黑主题
        self.setStyleSheet(self._get_dark_theme())

        self.init_ui()
        self.load_audio_devices()

        # 应用保存的配置到界面
        self._apply_saved_config()

    def _apply_saved_config(self):
        """应用保存的配置到界面"""
        try:
            # 应用API配置
            if hasattr(self, 'api_key_input') and self.saved_config.get('api_key'):
                self.api_key_input.setText(self.saved_config['api_key'])

            if hasattr(self, 'base_url_input') and self.saved_config.get('base_url'):
                self.base_url_input.setText(self.saved_config['base_url'])

            if hasattr(self, 'model_combo') and self.saved_config.get('model'):
                index = self.model_combo.findText(self.saved_config['model'])
                if index >= 0:
                    self.model_combo.setCurrentIndex(index)

            # 应用提示词
            if hasattr(self, 'prompt_text') and self.saved_config.get('prompt'):
                self.prompt_text.setPlainText(self.saved_config['prompt'])

            # 应用热词
            if hasattr(self, 'hotwords_text') and self.saved_config.get('hotwords'):
                self.hotwords_text.setPlainText('\n'.join(self.saved_config['hotwords']))

            # 应用字体大小
            if hasattr(self, 'typewriter_display') and self.saved_config.get('font_size'):
                font = self.typewriter_display.font()
                font.setPointSize(self.saved_config['font_size'])
                self.typewriter_display.setFont(font)

            # 应用界面语言设置
            if hasattr(self, 'ui_language_combo'):
                for i in range(self.ui_language_combo.count()):
                    if self.ui_language_combo.itemData(i) == self.saved_lang:
                        self.ui_language_combo.setCurrentIndex(i)
                        break

        except Exception as e:
            logger.error(f"应用保存的配置失败: {e}")

    def _save_current_config(self):
        """保存当前配置"""
        try:
            config_to_save = {
                'ui_language': self.lang_manager.current_language,
                'api_key': getattr(self, 'api_key_input', None) and self.api_key_input.text().strip() or '',
                'base_url': getattr(self, 'base_url_input',
                                    None) and self.base_url_input.text().strip() or 'https://api.openai.com/v1',
                'model': getattr(self, 'model_combo', None) and self.model_combo.currentText() or 'gpt-4o-transcribe',
                'language': getattr(self, 'language_combo', None) and (
                            self.language_combo.currentData() or self.language_combo.currentText()) or 'zh',
                'prompt': getattr(self, 'prompt_text', None) and self.prompt_text.toPlainText() or '',
                'hotwords': getattr(self, 'hotwords_text', None) and [line.strip() for line in
                                                                      self.hotwords_text.toPlainText().split('\n') if
                                                                      line.strip()] or [],
                'font_size': getattr(self, 'typewriter_display',
                                     None) and self.typewriter_display.font().pointSize() or 18
            }

            self.config_manager.save_config(config_to_save)
        except Exception as e:
            logger.error(f"保存配置失败: {e}")

    def _handle_exception(self, exc_type, exc_value, exc_traceback):
        """全局异常处理器"""
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        logger.error(f"未处理的异常: {error_msg}")

        self.error_count += 1
        if self.error_count < self.max_errors:
            QMessageBox.critical(self,
                                 self.lang_manager.get_text('dialog_program_error'),
                                 f"{self.lang_manager.get_text('dialog_unexpected_error')}:\n{str(exc_value)}\n\n{self.lang_manager.get_text('dialog_error_logged')}")
        else:
            QMessageBox.critical(self,
                                 self.lang_manager.get_text('dialog_program_error'),
                                 self.lang_manager.get_text('dialog_too_many_errors'))
            self.close()

    def center_window(self):
        """窗口居中显示"""
        try:
            desktop = QDesktopWidget()
            screen_rect = desktop.screenGeometry()
            window_size = self.size()
            x = (screen_rect.width() - window_size.width()) // 2
            y = (screen_rect.height() - window_size.height()) // 2
            self.move(x, y)
        except Exception as e:
            logger.error(f"窗口居中失败: {e}")

    def _get_default_config(self):
        """获取默认配置"""
        return {
            'model': 'gpt-4o-transcribe',
            'language': 'zh',
            'temperature': 0.05,
            'use_streaming': True,
            'silence_threshold': 0.001,
            'min_audio_length': 0.02,
            'vad_threshold': 0.15,
            'silence_duration_ms': 300,
            'prompt': 'Please provide accurate and fluent real-time transcription. Pay attention to segmentation.',
            'hotwords': [],
            'base_url': 'https://api.openai.com/v1',
            'api_key': '',
            'output_format': 'text',
            'audio_filter_enabled': True,
            'noise_gate_enabled': True,
            'noise_reduction_level': 0.3,
            'typewriter_speed_ms': 12
        }

    def init_ui(self):
        """初始化界面"""
        try:
            self.setWindowTitle(self.lang_manager.get_text('window_title'))
            self.setGeometry(50, 50, 1800, 900)

            central_widget = QWidget()
            self.setCentralWidget(central_widget)

            main_layout = QHBoxLayout()
            main_layout.setSpacing(15)
            main_layout.setContentsMargins(15, 15, 15, 15)

            # 创建水平分割器
            splitter = QSplitter(Qt.Horizontal)
            splitter.setHandleWidth(8)
            splitter.setStyleSheet("""
                QSplitter::handle {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                        stop:0 #00FF7F, stop:1 #FFD700);
                    border-radius: 4px;
                    margin: 2px;
                }
                QSplitter::handle:hover {
                    background: #00FF7F;
                }
            """)

            # 左侧：控制面板
            control_panel = self._create_control_panel()
            control_panel.setMinimumWidth(600)
            control_panel.setMaximumWidth(800)
            splitter.addWidget(control_panel)

            # 右侧：音频监控 + 字幕显示
            right_panel = self._create_right_panel()
            right_panel.setMinimumWidth(900)
            splitter.addWidget(right_panel)

            # 设置分割器比例
            splitter.setSizes([700, 1100])
            splitter.setStretchFactor(0, 1)
            splitter.setStretchFactor(1, 2)

            main_layout.addWidget(splitter)
            central_widget.setLayout(main_layout)

            QTimer.singleShot(100, self.center_window)
        except Exception as e:
            logger.error(f"初始化界面失败: {e}")
            raise

    def _create_control_panel(self):
        """创建控制面板"""
        try:
            panel = QFrame()
            panel.setFrameStyle(QFrame.StyledPanel)
            layout = QVBoxLayout()
            layout.setSpacing(10)

            # 标题
            self.title_label = QLabel(self.lang_manager.get_text('main_title'))
            self.title_label.setStyleSheet("""
                font-size: 24px; 
                font-weight: bold; 
                color: #00FF7F; 
                padding: 15px;
                border-bottom: 3px solid #00FF7F;
                margin-bottom: 15px;
            """)
            layout.addWidget(self.title_label)

            # 添加广告位 - 软件技术支持
            self.ad_label = QLabel(self.lang_manager.get_text('tech_support'))
            self.ad_label.setStyleSheet("""
                font-size: 14px; 
                font-weight: bold; 
                color: #FFD700; 
                background: rgba(255, 215, 0, 0.1);
                padding: 8px 15px;
                border: 1px solid #FFD700;
                border-radius: 6px;
                margin-bottom: 10px;
                text-align: center;
            """)
            self.ad_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(self.ad_label)

            # 标签页
            self.tab_widget = QTabWidget()
            self.tab_widget.setStyleSheet("""
                QTabWidget::pane {
                    border: 1px solid #404040;
                    background: #1a1a1a;
                    border-radius: 8px;
                }
                QTabBar::tab {
                    background: #2a2a2a;
                    color: #CCCCCC;
                    padding: 12px 18px;
                    margin-right: 3px;
                    border-top-left-radius: 8px;
                    border-top-right-radius: 8px;
                    font-size: 15px;
                    font-weight: bold;
                    min-width: 80px;
                }
                QTabBar::tab:selected {
                    background: #00FF7F;
                    color: #000000;
                }
                QTabBar::tab:hover {
                    background: #404040;
                }
            """)

            # 基本设置
            basic_tab = self._create_basic_tab()
            self.tab_widget.addTab(basic_tab, self.lang_manager.get_text('tab_basic'))

            # 实时设置
            realtime_tab = self._create_realtime_tab()
            self.tab_widget.addTab(realtime_tab, self.lang_manager.get_text('tab_realtime'))

            # 热词设置
            hotwords_tab = self._create_hotwords_tab()
            self.tab_widget.addTab(hotwords_tab, self.lang_manager.get_text('tab_hotwords'))

            # 高级设置
            advanced_tab = self._create_advanced_tab()
            self.tab_widget.addTab(advanced_tab, self.lang_manager.get_text('tab_advanced'))

            layout.addWidget(self.tab_widget)

            # 控制按钮
            self._add_control_buttons(layout)

            # 状态指示器
            self._add_status_indicators(layout)

            panel.setLayout(layout)
            return panel
        except Exception as e:
            logger.error(f"创建控制面板失败: {e}")
            raise

    def _create_basic_tab(self):
        """创建基本设置标签页"""
        try:
            widget = QWidget()
            layout = QVBoxLayout()
            layout.setSpacing(12)

            # 界面语言设置组 - 新增
            language_group = QGroupBox(self.lang_manager.get_text('group_language'))
            language_group.setStyleSheet(self._get_group_style("#00FF7F"))
            language_layout = QHBoxLayout()
            language_layout.setSpacing(10)

            self.language_label = QLabel(self.lang_manager.get_text('label_language'))
            language_layout.addWidget(self.language_label)
            self.ui_language_combo = QComboBox()
            for lang_code, lang_name in self.lang_manager.languages.items():
                self.ui_language_combo.addItem(lang_name, lang_code)
            self.ui_language_combo.setCurrentText(
                self.lang_manager.get_language_name(self.lang_manager.current_language))
            self.ui_language_combo.currentTextChanged.connect(self._change_ui_language)
            self.ui_language_combo.setMinimumHeight(35)
            language_layout.addWidget(self.ui_language_combo, 1)

            language_group.setLayout(language_layout)
            layout.addWidget(language_group)

            # API配置组
            self.api_group = QGroupBox(self.lang_manager.get_text('group_api'))
            self.api_group.setStyleSheet(self._get_group_style())
            api_layout = QGridLayout()
            api_layout.setSpacing(10)

            # API Key
            self.api_key_label = QLabel(self.lang_manager.get_text('label_api_key'))
            api_layout.addWidget(self.api_key_label, 0, 0)
            self.api_key_input = QLineEdit()
            self.api_key_input.setEchoMode(QLineEdit.Password)
            self.api_key_input.setPlaceholderText(self.lang_manager.get_text('placeholder_api_key'))
            self.api_key_input.setMinimumHeight(35)
            api_layout.addWidget(self.api_key_input, 0, 1, 1, 2)

            # API端点
            self.endpoint_label = QLabel(self.lang_manager.get_text('label_endpoint'))
            api_layout.addWidget(self.endpoint_label, 1, 0)
            self.base_url_input = QLineEdit()
            self.base_url_input.setText("https://api.openai.com/v1")
            self.base_url_input.setMinimumHeight(35)
            api_layout.addWidget(self.base_url_input, 1, 1, 1, 2)

            # 模型
            self.model_label = QLabel(self.lang_manager.get_text('label_model'))
            api_layout.addWidget(self.model_label, 2, 0)
            self.model_combo = QComboBox()
            self.model_combo.addItems(['gpt-4o-transcribe', 'gpt-4o-mini-transcribe', 'whisper-1'])
            self.model_combo.currentTextChanged.connect(self._update_config)
            self.model_combo.setMinimumHeight(35)
            api_layout.addWidget(self.model_combo, 2, 1)

            # 语言 - 支持更多语种
            self.language_model_label = QLabel(self.lang_manager.get_text('label_language_model'))
            api_layout.addWidget(self.language_model_label, 2, 2)
            self.language_combo = QComboBox()
            languages = [
                ('auto', self.lang_manager.get_text('language_auto')),
                ('zh', self.lang_manager.get_text('language_chinese')),
                ('en', self.lang_manager.get_text('language_english')),
                ('ja', self.lang_manager.get_text('language_japanese')),
                ('ko', self.lang_manager.get_text('language_korean')),
                ('fr', self.lang_manager.get_text('language_french')),
                ('de', self.lang_manager.get_text('language_german')),
                ('es', self.lang_manager.get_text('language_spanish')),
                ('it', self.lang_manager.get_text('language_italian')),
                ('pt', self.lang_manager.get_text('language_portuguese')),
                ('ru', self.lang_manager.get_text('language_russian')),
                ('ar', self.lang_manager.get_text('language_arabic')),
                ('hi', self.lang_manager.get_text('language_hindi')),
                ('th', self.lang_manager.get_text('language_thai')),
                ('vi', self.lang_manager.get_text('language_vietnamese'))
            ]
            for code, name in languages:
                self.language_combo.addItem(name, code)
            self.language_combo.currentTextChanged.connect(self._update_config)
            self.language_combo.setMinimumHeight(35)
            api_layout.addWidget(self.language_combo, 2, 3)

            self.api_group.setLayout(api_layout)
            layout.addWidget(self.api_group)

            # 设备配置组
            self.device_group = QGroupBox(self.lang_manager.get_text('group_device'))
            self.device_group.setStyleSheet(self._get_group_style())
            device_layout = QHBoxLayout()
            device_layout.setSpacing(10)

            self.device_label = QLabel(self.lang_manager.get_text('label_device'))
            device_layout.addWidget(self.device_label)
            self.device_combo = QComboBox()
            self.device_combo.setMinimumHeight(35)
            device_layout.addWidget(self.device_combo, 1)

            self.refresh_btn = QPushButton(self.lang_manager.get_text('btn_refresh'))
            self.refresh_btn.setMaximumWidth(80)
            self.refresh_btn.setMinimumHeight(35)
            self.refresh_btn.clicked.connect(self.load_audio_devices)
            device_layout.addWidget(self.refresh_btn)

            self.device_group.setLayout(device_layout)
            layout.addWidget(self.device_group)

            # 提示词设置组 - 从热词标签页移动到这里
            self.prompt_group = QGroupBox(self.lang_manager.get_text('group_prompt'))
            self.prompt_group.setStyleSheet(self._get_group_style())
            prompt_layout = QVBoxLayout()
            prompt_layout.setSpacing(10)

            self.prompt_help_label = QLabel(self.lang_manager.get_text('help_prompt'))
            self.prompt_help_label.setStyleSheet("color: #888888; font-size: 13px; margin-bottom: 5px;")
            prompt_layout.addWidget(self.prompt_help_label)

            self.prompt_text = QTextEdit()
            self.prompt_text.setMaximumHeight(80)
            self.prompt_text.setMinimumHeight(60)
            self.prompt_text.setPlaceholderText(self.lang_manager.get_text('placeholder_prompt'))
            self.prompt_text.setPlainText(self.current_config['prompt'])
            self.prompt_text.textChanged.connect(self._update_config)
            prompt_layout.addWidget(self.prompt_text)

            # 提示词预设按钮
            prompt_preset_layout = QHBoxLayout()
            prompt_preset_layout.setSpacing(8)

            self.general_prompt_btn = QPushButton(self.lang_manager.get_text('btn_general'))
            self.general_prompt_btn.setMaximumHeight(30)
            self.general_prompt_btn.clicked.connect(lambda: self._set_preset_prompt(
                self.lang_manager.get_text('preset_general')
            ))
            prompt_preset_layout.addWidget(self.general_prompt_btn)

            self.tech_prompt_btn = QPushButton(self.lang_manager.get_text('btn_tech'))
            self.tech_prompt_btn.setMaximumHeight(30)
            self.tech_prompt_btn.clicked.connect(lambda: self._set_preset_prompt(
                self.lang_manager.get_text('preset_tech')
            ))
            prompt_preset_layout.addWidget(self.tech_prompt_btn)

            self.business_prompt_btn = QPushButton(self.lang_manager.get_text('btn_business'))
            self.business_prompt_btn.setMaximumHeight(30)
            self.business_prompt_btn.clicked.connect(lambda: self._set_preset_prompt(
                self.lang_manager.get_text('preset_business')
            ))
            prompt_preset_layout.addWidget(self.business_prompt_btn)

            self.medical_prompt_btn = QPushButton(self.lang_manager.get_text('btn_medical'))
            self.medical_prompt_btn.setMaximumHeight(30)
            self.medical_prompt_btn.clicked.connect(lambda: self._set_preset_prompt(
                self.lang_manager.get_text('preset_medical')
            ))
            prompt_preset_layout.addWidget(self.medical_prompt_btn)

            self.clear_prompt_btn = QPushButton(self.lang_manager.get_text('btn_clear'))
            self.clear_prompt_btn.setMaximumHeight(30)
            self.clear_prompt_btn.clicked.connect(self.prompt_text.clear)
            prompt_preset_layout.addWidget(self.clear_prompt_btn)

            prompt_layout.addLayout(prompt_preset_layout)
            self.prompt_group.setLayout(prompt_layout)
            layout.addWidget(self.prompt_group)

            layout.addStretch()
            widget.setLayout(layout)
            return widget
        except Exception as e:
            logger.error(f"创建基本设置标签页失败: {e}")
            return QWidget()

    def _create_realtime_tab(self):
        """创建实时设置标签页"""
        try:
            widget = QWidget()
            layout = QVBoxLayout()
            layout.setSpacing(12)

            # 实时VAD设置
            self.vad_group = QGroupBox(self.lang_manager.get_text('group_vad'))
            self.vad_group.setStyleSheet(self._get_group_style("#FFD700"))
            vad_layout = QVBoxLayout()
            vad_layout.setSpacing(10)

            # VAD阈值
            self.sensitivity_label = QLabel(self.lang_manager.get_text('label_sensitivity'))
            vad_layout.addWidget(self.sensitivity_label)
            sensitivity_layout = QHBoxLayout()
            self.vad_slider = QSlider(Qt.Horizontal)
            self.vad_slider.setRange(5, 50)
            self.vad_slider.setValue(15)
            self.vad_slider.valueChanged.connect(self._update_vad_threshold)
            self.vad_label = QLabel("0.15")
            self.vad_label.setStyleSheet("font-weight: bold; color: #FFD700; min-width: 50px;")
            sensitivity_layout.addWidget(self.vad_slider)
            sensitivity_layout.addWidget(self.vad_label)
            vad_layout.addLayout(sensitivity_layout)

            # 静音提交间隔
            self.silence_interval_label = QLabel(self.lang_manager.get_text('label_silence_interval'))
            vad_layout.addWidget(self.silence_interval_label)
            silence_layout = QHBoxLayout()
            self.silence_duration_slider = QSlider(Qt.Horizontal)
            self.silence_duration_slider.setRange(100, 800)
            self.silence_duration_slider.setValue(200)
            self.silence_duration_slider.valueChanged.connect(self._update_silence_duration)
            self.silence_duration_label = QLabel(f"300{self.lang_manager.get_text('unit_ms')}")
            self.silence_duration_label.setStyleSheet("font-weight: bold; color: #FFD700; min-width: 60px;")
            silence_layout.addWidget(self.silence_duration_slider)
            silence_layout.addWidget(self.silence_duration_label)
            vad_layout.addLayout(silence_layout)

            self.vad_group.setLayout(vad_layout)
            layout.addWidget(self.vad_group)

            # 音频质量增强
            self.audio_group = QGroupBox(self.lang_manager.get_text('group_audio_enhance'))
            self.audio_group.setStyleSheet(self._get_group_style("#FFD700"))
            audio_layout = QVBoxLayout()
            audio_layout.setSpacing(10)

            self.audio_filter_checkbox = QCheckBox(self.lang_manager.get_text('checkbox_audio_filter'))
            self.audio_filter_checkbox.setChecked(True)
            self.audio_filter_checkbox.stateChanged.connect(self._update_config)
            audio_layout.addWidget(self.audio_filter_checkbox)

            self.noise_gate_checkbox = QCheckBox(self.lang_manager.get_text('checkbox_noise_gate'))
            self.noise_gate_checkbox.setChecked(True)
            self.noise_gate_checkbox.stateChanged.connect(self._update_config)
            audio_layout.addWidget(self.noise_gate_checkbox)

            # 噪音抑制级别
            self.noise_reduction_label = QLabel(self.lang_manager.get_text('label_noise_reduction'))
            audio_layout.addWidget(self.noise_reduction_label)
            noise_layout = QHBoxLayout()
            self.noise_reduction_slider = QSlider(Qt.Horizontal)
            self.noise_reduction_slider.setRange(0, 50)
            self.noise_reduction_slider.setValue(30)
            self.noise_reduction_slider.valueChanged.connect(self._update_noise_reduction)
            self.noise_reduction_display_label = QLabel(f"30{self.lang_manager.get_text('unit_percent')}")
            self.noise_reduction_display_label.setStyleSheet("font-weight: bold; color: #FFD700; min-width: 50px;")
            noise_layout.addWidget(self.noise_reduction_slider)
            noise_layout.addWidget(self.noise_reduction_display_label)
            audio_layout.addLayout(noise_layout)

            self.audio_group.setLayout(audio_layout)
            layout.addWidget(self.audio_group)

            # 打字机效果设置
            self.typewriter_group = QGroupBox(self.lang_manager.get_text('group_display'))
            self.typewriter_group.setStyleSheet(self._get_group_style("#FFD700"))
            typewriter_layout = QVBoxLayout()
            typewriter_layout.setSpacing(10)

            # 换行控制
            self.line_break_label = QLabel(self.lang_manager.get_text('label_line_break'))
            typewriter_layout.addWidget(self.line_break_label)
            line_break_layout = QHBoxLayout()
            self.line_break_slider = QSlider(Qt.Horizontal)
            self.line_break_slider.setRange(3, 15)
            self.line_break_slider.setValue(5)
            self.line_break_slider.valueChanged.connect(self._update_line_break_interval)
            self.line_break_display_label = QLabel(f"7{self.lang_manager.get_text('unit_sentences')}")
            self.line_break_display_label.setStyleSheet("font-weight: bold; color: #FFD700; min-width: 50px;")
            line_break_layout.addWidget(self.line_break_slider)
            line_break_layout.addWidget(self.line_break_display_label)
            typewriter_layout.addLayout(line_break_layout)

            # 打字速度
            self.typing_speed_label = QLabel(self.lang_manager.get_text('label_typing_speed'))
            typewriter_layout.addWidget(self.typing_speed_label)
            speed_layout = QHBoxLayout()
            self.typewriter_speed_slider = QSlider(Qt.Horizontal)
            self.typewriter_speed_slider.setRange(5, 30)
            self.typewriter_speed_slider.setValue(12)
            self.typewriter_speed_slider.valueChanged.connect(self._update_typewriter_speed)
            self.typewriter_speed_display_label = QLabel(f"12{self.lang_manager.get_text('unit_ms_per_char')}")
            self.typewriter_speed_display_label.setStyleSheet("font-weight: bold; color: #FFD700; min-width: 80px;")
            speed_layout.addWidget(self.typewriter_speed_slider)
            speed_layout.addWidget(self.typewriter_speed_display_label)
            typewriter_layout.addLayout(speed_layout)

            self.typewriter_group.setLayout(typewriter_layout)
            layout.addWidget(self.typewriter_group)

            layout.addStretch()
            widget.setLayout(layout)
            return widget
        except Exception as e:
            logger.error(f"创建实时设置标签页失败: {e}")
            return QWidget()

    def _create_hotwords_tab(self):
        """创建热词标签页"""
        try:
            widget = QWidget()
            layout = QVBoxLayout()
            layout.setSpacing(12)

            # 热词组
            self.hotwords_group = QGroupBox(self.lang_manager.get_text('group_hotwords'))
            self.hotwords_group.setStyleSheet(self._get_group_style("#FFD700"))
            hotwords_layout = QVBoxLayout()
            hotwords_layout.setSpacing(10)

            self.hotwords_help_label = QLabel(self.lang_manager.get_text('help_hotwords'))
            self.hotwords_help_label.setStyleSheet("color: #888888; font-size: 13px; margin-bottom: 5px;")
            hotwords_layout.addWidget(self.hotwords_help_label)

            self.hotwords_text = QTextEdit()
            self.hotwords_text.setMaximumHeight(140)
            self.hotwords_text.setMinimumHeight(120)
            self.hotwords_text.setPlaceholderText(self.lang_manager.get_text('placeholder_hotwords'))
            self.hotwords_text.textChanged.connect(self._update_hotwords)
            hotwords_layout.addWidget(self.hotwords_text)

            # 预设按钮组
            preset_layout = QGridLayout()
            preset_layout.setSpacing(8)

            self.ai_btn = QPushButton(self.lang_manager.get_text('btn_ai_words'))
            self.ai_btn.clicked.connect(lambda: self._add_preset_hotwords(
                self.lang_manager.texts['hotwords_ai']
            ))
            preset_layout.addWidget(self.ai_btn, 0, 0)

            self.tech_btn = QPushButton(self.lang_manager.get_text('btn_tech_words'))
            self.tech_btn.clicked.connect(lambda: self._add_preset_hotwords(
                self.lang_manager.texts['hotwords_tech']
            ))
            preset_layout.addWidget(self.tech_btn, 0, 1)

            self.business_btn = QPushButton(self.lang_manager.get_text('btn_business_words'))
            self.business_btn.clicked.connect(lambda: self._add_preset_hotwords(
                self.lang_manager.texts['hotwords_business']
            ))
            preset_layout.addWidget(self.business_btn, 0, 2)

            self.medical_btn = QPushButton(self.lang_manager.get_text('btn_medical_words'))
            self.medical_btn.clicked.connect(lambda: self._add_preset_hotwords(
                self.lang_manager.texts['hotwords_medical']
            ))
            preset_layout.addWidget(self.medical_btn, 1, 0)

            self.edu_btn = QPushButton(self.lang_manager.get_text('btn_edu_words'))
            self.edu_btn.clicked.connect(lambda: self._add_preset_hotwords(
                self.lang_manager.texts['hotwords_education']
            ))
            preset_layout.addWidget(self.edu_btn, 1, 1)

            self.clear_hotwords_btn = QPushButton(self.lang_manager.get_text('btn_clear'))
            self.clear_hotwords_btn.clicked.connect(self.hotwords_text.clear)
            preset_layout.addWidget(self.clear_hotwords_btn, 1, 2)

            hotwords_layout.addLayout(preset_layout)
            self.hotwords_group.setLayout(hotwords_layout)
            layout.addWidget(self.hotwords_group)

            # 热词使用说明
            self.usage_group = QGroupBox(self.lang_manager.get_text('group_usage'))
            self.usage_group.setStyleSheet(self._get_group_style("#FFD700"))
            usage_layout = QVBoxLayout()
            usage_layout.setSpacing(8)

            self.usage_text = QLabel(self.lang_manager.get_text('usage_text'))
            self.usage_text.setStyleSheet("""
                color: #CCCCCC; 
                font-size: 13px; 
                line-height: 1.6;
                padding: 10px;
                background: rgba(255, 215, 0, 0.05);
                border-radius: 6px;
            """)
            self.usage_text.setWordWrap(True)
            usage_layout.addWidget(self.usage_text)

            self.usage_group.setLayout(usage_layout)
            layout.addWidget(self.usage_group)

            layout.addStretch()
            widget.setLayout(layout)
            return widget
        except Exception as e:
            logger.error(f"创建热词标签页失败: {e}")
            return QWidget()

    def _set_preset_prompt(self, prompt_text):
        """设置预设提示词"""
        try:
            if hasattr(self, 'prompt_text'):
                self.prompt_text.setPlainText(prompt_text)
                self._update_config()
                self._update_status(self.lang_manager.get_text('status_preset_prompt_set'), "#00FF7F")
        except Exception as e:
            logger.error(f"设置预设提示词失败: {e}")

    def _create_advanced_tab(self):
        """创建高级设置标签页"""
        try:
            widget = QWidget()
            layout = QVBoxLayout()
            layout.setSpacing(12)

            # 网络设置组
            self.network_group = QGroupBox(self.lang_manager.get_text('group_network'))
            self.network_group.setStyleSheet(self._get_group_style("#FF6B6B"))
            network_layout = QVBoxLayout()
            network_layout.setSpacing(10)

            # 连接超时
            self.timeout_label = QLabel(self.lang_manager.get_text('label_timeout'))
            network_layout.addWidget(self.timeout_label)
            timeout_layout = QHBoxLayout()
            self.timeout_slider = QSlider(Qt.Horizontal)
            self.timeout_slider.setRange(5, 30)
            self.timeout_slider.setValue(10)
            self.timeout_slider.valueChanged.connect(self._update_timeout)
            self.timeout_display_label = QLabel(f"10{self.lang_manager.get_text('unit_seconds')}")
            self.timeout_display_label.setStyleSheet("font-weight: bold; color: #FF6B6B; min-width: 50px;")
            timeout_layout.addWidget(self.timeout_slider)
            timeout_layout.addWidget(self.timeout_display_label)
            network_layout.addLayout(timeout_layout)

            # 重连设置
            self.reconnect_label = QLabel(self.lang_manager.get_text('label_reconnect'))
            network_layout.addWidget(self.reconnect_label)
            reconnect_layout = QHBoxLayout()
            self.reconnect_slider = QSlider(Qt.Horizontal)
            self.reconnect_slider.setRange(3, 10)
            self.reconnect_slider.setValue(5)
            self.reconnect_slider.valueChanged.connect(self._update_reconnect)
            self.reconnect_display_label = QLabel(f"5{self.lang_manager.get_text('unit_times')}")
            self.reconnect_display_label.setStyleSheet("font-weight: bold; color: #FF6B6B; min-width: 50px;")
            reconnect_layout.addWidget(self.reconnect_slider)
            reconnect_layout.addWidget(self.reconnect_display_label)
            network_layout.addLayout(reconnect_layout)

            self.network_group.setLayout(network_layout)
            layout.addWidget(self.network_group)

            # 性能优化组
            self.perf_group = QGroupBox(self.lang_manager.get_text('group_performance'))
            self.perf_group.setStyleSheet(self._get_group_style("#FF6B6B"))
            perf_layout = QVBoxLayout()
            perf_layout.setSpacing(10)

            self.ultra_mode_checkbox = QCheckBox(self.lang_manager.get_text('checkbox_ultra_mode'))
            self.ultra_mode_checkbox.setChecked(True)
            self.ultra_mode_checkbox.stateChanged.connect(self._update_config)
            self.ultra_mode_checkbox.setStyleSheet("font-size: 15px; font-weight: bold; color: #FF6B6B;")
            perf_layout.addWidget(self.ultra_mode_checkbox)

            self.aggressive_cleanup_checkbox = QCheckBox(self.lang_manager.get_text('checkbox_aggressive_cleanup'))
            self.aggressive_cleanup_checkbox.setChecked(True)
            self.aggressive_cleanup_checkbox.stateChanged.connect(self._update_config)
            perf_layout.addWidget(self.aggressive_cleanup_checkbox)

            self.perf_group.setLayout(perf_layout)
            layout.addWidget(self.perf_group)

            # 调试组
            self.debug_group = QGroupBox(self.lang_manager.get_text('group_debug'))
            self.debug_group.setStyleSheet(self._get_group_style("#FF6B6B"))
            debug_layout = QVBoxLayout()
            debug_layout.setSpacing(10)

            self.debug_mode_checkbox = QCheckBox(self.lang_manager.get_text('checkbox_debug_mode'))
            self.debug_mode_checkbox.setChecked(False)
            self.debug_mode_checkbox.stateChanged.connect(self._update_config)
            debug_layout.addWidget(self.debug_mode_checkbox)

            self.debug_group.setLayout(debug_layout)
            layout.addWidget(self.debug_group)

            layout.addStretch()
            widget.setLayout(layout)
            return widget
        except Exception as e:
            logger.error(f"创建高级设置标签页失败: {e}")
            return QWidget()

    def _get_group_style(self, title_color="#00FF7F"):
        """获取组框样式"""
        return f"""
            QGroupBox {{
                font-size: 16px;
                font-weight: bold;
                padding-top: 18px;
                border: 1px solid #404040;
                border-radius: 8px;
                margin-top: 10px;
                color: #CCCCCC;
            }}
            QGroupBox::title {{
                color: {title_color};
                padding: 0 10px;
            }}
        """

    def _create_right_panel(self):
        """创建右侧面板"""
        try:
            panel = QFrame()
            panel.setFrameStyle(QFrame.StyledPanel)
            layout = QVBoxLayout()
            layout.setSpacing(10)
            layout.setContentsMargins(10, 10, 10, 10)

            # 创建垂直分割器
            vertical_splitter = QSplitter(Qt.Vertical)
            vertical_splitter.setHandleWidth(6)
            vertical_splitter.setStyleSheet("""
                QSplitter::handle {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                        stop:0 #00FF7F, stop:1 #FFD700);
                    border-radius: 3px;
                    margin: 1px;
                }
                QSplitter::handle:hover {
                    background: #00FF7F;
                }
            """)

            # 上方：音频监控面板
            audio_monitor_panel = self._create_audio_monitor()
            audio_monitor_panel.setMinimumHeight(150)
            audio_monitor_panel.setMaximumHeight(200)
            vertical_splitter.addWidget(audio_monitor_panel)

            # 下方：字幕显示区域
            subtitle_panel = self._create_subtitle_area()
            subtitle_panel.setMinimumHeight(500)
            vertical_splitter.addWidget(subtitle_panel)

            # 设置分割器比例
            vertical_splitter.setSizes([180, 700])
            vertical_splitter.setStretchFactor(0, 0)
            vertical_splitter.setStretchFactor(1, 1)

            layout.addWidget(vertical_splitter)
            panel.setLayout(layout)
            return panel
        except Exception as e:
            logger.error(f"创建右侧面板失败: {e}")
            return QFrame()

    def _create_audio_monitor(self):
        """创建音频监控面板"""
        try:
            panel = QFrame()
            panel.setFrameStyle(QFrame.StyledPanel)
            layout = QVBoxLayout()
            layout.setSpacing(8)
            layout.setContentsMargins(10, 8, 10, 8)

            # 标题
            self.audio_title = QLabel(self.lang_manager.get_text('audio_monitor_title'))
            self.audio_title.setStyleSheet("""
                font-size: 18px; 
                font-weight: bold; 
                color: #00FF7F; 
                padding: 6px;
                border-bottom: 2px solid #00FF7F;
                margin-bottom: 6px;
            """)
            layout.addWidget(self.audio_title)

            # 音频显示区域
            audio_layout = QHBoxLayout()
            audio_layout.setSpacing(8)

            # 波形显示
            wave_container = QFrame()
            wave_container.setFrameStyle(QFrame.StyledPanel)
            wave_layout = QVBoxLayout()
            wave_layout.setContentsMargins(5, 5, 5, 5)

            self.wave_label = QLabel(self.lang_manager.get_text('audio_waveform'))
            self.wave_label.setStyleSheet("color: #CCCCCC; font-size: 12px; font-weight: bold;")
            wave_layout.addWidget(self.wave_label)

            self.audio_visualizer = CompactAudioVisualizer()
            wave_layout.addWidget(self.audio_visualizer)

            wave_container.setLayout(wave_layout)
            audio_layout.addWidget(wave_container, 4)

            # 音量指示器
            volume_container = QFrame()
            volume_container.setFrameStyle(QFrame.StyledPanel)
            volume_layout = QVBoxLayout()
            volume_layout.setContentsMargins(5, 5, 5, 5)

            self.volume_label = QLabel(self.lang_manager.get_text('audio_volume'))
            self.volume_label.setStyleSheet("color: #CCCCCC; font-size: 12px; font-weight: bold;")
            volume_layout.addWidget(self.volume_label)

            volume_content_layout = QHBoxLayout()

            self.volume_indicator = CompactVolumeIndicator()
            volume_content_layout.addWidget(self.volume_indicator)

            # 音量信息
            volume_info_layout = QVBoxLayout()
            volume_info_layout.setSpacing(2)

            self.volume_level_label = QLabel("0%")
            self.volume_level_label.setStyleSheet("font-size: 12px; font-weight: bold; color: #00FF7F;")
            volume_info_layout.addWidget(self.volume_level_label)

            self.peak_level_label = QLabel(f"{self.lang_manager.get_text('audio_peak')}: 0%")
            self.peak_level_label.setStyleSheet("font-size: 10px; color: #888888;")
            volume_info_layout.addWidget(self.peak_level_label)

            self.noise_level_label = QLabel(self.lang_manager.get_text('audio_quiet'))
            self.noise_level_label.setStyleSheet("font-size: 10px; color: #888888;")
            volume_info_layout.addWidget(self.noise_level_label)

            volume_info_layout.addStretch()
            volume_content_layout.addLayout(volume_info_layout)

            volume_layout.addLayout(volume_content_layout)
            volume_container.setLayout(volume_layout)
            audio_layout.addWidget(volume_container, 1)

            # 统计信息
            stats_container = QFrame()
            stats_container.setFrameStyle(QFrame.StyledPanel)
            stats_layout = QVBoxLayout()
            stats_layout.setContentsMargins(5, 5, 5, 5)

            self.stats_label = QLabel(self.lang_manager.get_text('audio_stats'))
            self.stats_label.setStyleSheet("color: #CCCCCC; font-size: 12px; font-weight: bold;")
            stats_layout.addWidget(self.stats_label)

            self.session_time_label = QLabel("00:00:00")
            self.session_time_label.setStyleSheet("color: #CCCCCC; font-size: 11px; font-weight: bold;")
            stats_layout.addWidget(self.session_time_label)

            self.total_chars_label = QLabel(f"{self.lang_manager.get_text('audio_chars')}: 0")
            self.total_chars_label.setStyleSheet("color: #CCCCCC; font-size: 10px;")
            stats_layout.addWidget(self.total_chars_label)

            self.avg_speed_label = QLabel(f"0 {self.lang_manager.get_text('unit_chars_per_min')}")
            self.avg_speed_label.setStyleSheet("color: #CCCCCC; font-size: 10px;")
            stats_layout.addWidget(self.avg_speed_label)

            stats_layout.addStretch()
            stats_container.setLayout(stats_layout)
            audio_layout.addWidget(stats_container, 1)

            layout.addLayout(audio_layout)

            # 更新定时器
            self.update_timer = QTimer()
            self.update_timer.timeout.connect(self._update_displays)
            self.update_timer.start(50)

            panel.setLayout(layout)
            return panel
        except Exception as e:
            logger.error(f"创建音频监控面板失败: {e}")
            return QFrame()

    def _create_subtitle_area(self):
        """创建字幕显示区域"""
        try:
            widget = QFrame()
            widget.setFrameStyle(QFrame.StyledPanel)
            layout = QVBoxLayout()
            layout.setSpacing(10)
            layout.setContentsMargins(10, 10, 10, 10)

            # 标题栏
            header_layout = QHBoxLayout()

            self.subtitle_title = QLabel(self.lang_manager.get_text('subtitle_title'))
            self.subtitle_title.setStyleSheet("""
                font-size: 22px; 
                font-weight: bold; 
                color: #00FF7F; 
                padding: 12px;
            """)
            header_layout.addWidget(self.subtitle_title)

            header_layout.addStretch()

            # 功能按钮
            self.auto_scroll_btn = QPushButton(self.lang_manager.get_text('btn_auto_scroll'))
            self.auto_scroll_btn.setCheckable(True)
            self.auto_scroll_btn.setChecked(True)
            self.auto_scroll_btn.setMaximumWidth(120)
            header_layout.addWidget(self.auto_scroll_btn)

            self.font_size_btn = QPushButton(self.lang_manager.get_text('btn_font'))
            self.font_size_btn.setMaximumWidth(80)
            self.font_size_btn.clicked.connect(self._adjust_font_size)
            header_layout.addWidget(self.font_size_btn)

            layout.addLayout(header_layout)

            # 状态指示器
            status_layout = QHBoxLayout()

            self.realtime_indicator = QLabel(self.lang_manager.get_text('indicator_ready'))
            self.realtime_indicator.setStyleSheet("""
                color: #FFD700; 
                font-weight: bold; 
                font-size: 15px;
                padding: 8px 15px;
                background: rgba(255, 215, 0, 0.1);
                border-radius: 8px;
                border: 1px solid #FFD700;
            """)
            status_layout.addWidget(self.realtime_indicator)

            status_layout.addStretch()

            self.delay_indicator = QLabel(f"{self.lang_manager.get_text('subtitle_delay')}: <20ms")
            self.delay_indicator.setStyleSheet("color: #888888; font-size: 13px; font-weight: bold;")
            status_layout.addWidget(self.delay_indicator)

            self.typing_indicator = QLabel(self.lang_manager.get_text('indicator_waiting'))
            self.typing_indicator.setStyleSheet("color: #888888; font-size: 13px; font-weight: bold;")
            status_layout.addWidget(self.typing_indicator)

            layout.addLayout(status_layout)

            # 实时打字机显示组件
            self.typewriter_display = TypewriterDisplayWidget()
            layout.addWidget(self.typewriter_display)

            # 底部信息栏
            info_layout = QHBoxLayout()

            self.word_count_label = QLabel(f"{self.lang_manager.get_text('subtitle_word_count')}: 0")
            self.word_count_label.setStyleSheet("color: #888888; font-size: 13px; font-weight: bold;")
            info_layout.addWidget(self.word_count_label)

            self.typewriter_count_label = QLabel(f"{self.lang_manager.get_text('subtitle_active_items')}: 0")
            self.typewriter_count_label.setStyleSheet("color: #FFD700; font-size: 13px; font-weight: bold;")
            info_layout.addWidget(self.typewriter_count_label)

            info_layout.addStretch()

            self.format_label = QLabel(self.lang_manager.get_text('subtitle_format'))
            self.format_label.setStyleSheet("color: #888888; font-size: 13px; font-weight: bold;")
            info_layout.addWidget(self.format_label)

            layout.addLayout(info_layout)

            widget.setLayout(layout)
            return widget
        except Exception as e:
            logger.error(f"创建字幕显示区域失败: {e}")
            return QFrame()

    def _add_control_buttons(self, layout):
        """添加控制按钮"""
        try:
            button_layout = QVBoxLayout()
            button_layout.setSpacing(10)

            # 主控制按钮
            main_button_layout = QHBoxLayout()
            main_button_layout.setSpacing(10)

            self.start_button = QPushButton(self.lang_manager.get_text('btn_start'))
            self.start_button.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                        stop:0 #00FF7F, stop:1 #00D966);
                    color: black;
                    border: none;
                    padding: 15px;
                    border-radius: 10px;
                    font-size: 16px;
                    font-weight: bold;
                    min-height: 20px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                        stop:0 #00D966, stop:1 #00B359);
                }
            """)
            self.start_button.clicked.connect(self.start_transcription)
            main_button_layout.addWidget(self.start_button)

            self.stop_button = QPushButton(self.lang_manager.get_text('btn_stop'))
            self.stop_button.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                        stop:0 #FF4545, stop:1 #FF3333);
                    color: white;
                    border: none;
                    padding: 15px;
                    border-radius: 10px;
                    font-size: 16px;
                    font-weight: bold;
                    min-height: 20px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                        stop:0 #FF3333, stop:1 #FF2222);
                }
                QPushButton:disabled {
                    background: #404040;
                    color: #888888;
                }
            """)
            self.stop_button.clicked.connect(self.stop_transcription)
            self.stop_button.setEnabled(False)
            main_button_layout.addWidget(self.stop_button)

            button_layout.addLayout(main_button_layout)

            # 功能按钮组
            function_layout = QGridLayout()
            function_layout.setSpacing(8)

            button_style = """
                QPushButton {
                    background: #FFD700;
                    color: black;
                    border: none;
                    padding: 10px;
                    border-radius: 8px;
                    font-size: 14px;
                    font-weight: bold;
                    min-height: 15px;
                }
                QPushButton:hover {
                    background: #FFE033;
                }
            """

            self.clear_button = QPushButton(self.lang_manager.get_text('btn_clear'))
            self.clear_button.setStyleSheet(button_style)
            self.clear_button.clicked.connect(self.clear_display)
            function_layout.addWidget(self.clear_button, 0, 0)

            self.save_button = QPushButton(self.lang_manager.get_text('btn_save'))
            self.save_button.setStyleSheet(button_style)
            self.save_button.clicked.connect(self.save_transcription)
            function_layout.addWidget(self.save_button, 0, 1)

            self.load_file_button = QPushButton(self.lang_manager.get_text('btn_load_file'))
            self.load_file_button.setStyleSheet(button_style)
            self.load_file_button.clicked.connect(self.load_audio_file)
            function_layout.addWidget(self.load_file_button, 0, 2)

            self.copy_button = QPushButton(self.lang_manager.get_text('btn_copy'))
            self.copy_button.setStyleSheet(button_style)
            self.copy_button.clicked.connect(self._copy_transcription)
            function_layout.addWidget(self.copy_button, 1, 0)

            self.export_button = QPushButton(self.lang_manager.get_text('btn_export'))
            self.export_button.setStyleSheet(button_style)
            self.export_button.clicked.connect(self._export_transcription)
            function_layout.addWidget(self.export_button, 1, 1)

            self.settings_button = QPushButton(self.lang_manager.get_text('btn_settings'))
            self.settings_button.setStyleSheet(button_style)
            self.settings_button.clicked.connect(self._open_settings)
            function_layout.addWidget(self.settings_button, 1, 2)

            button_layout.addLayout(function_layout)

            # 进度条 - 优化颜色
            self.progress_bar = QProgressBar()
            self.progress_bar.setVisible(False)
            self.progress_bar.setStyleSheet("""
                QProgressBar {
                    border: 2px solid #404040;
                    border-radius: 8px;
                    text-align: center;
                    background: #2a2a2a;
                    color: #FFFFFF;
                    height: 25px;
                    font-weight: bold;
                    font-size: 15px;
                }
                QProgressBar::chunk {
                    background: #00FF7F;
                    border-radius: 6px;
                }
            """)
            button_layout.addWidget(self.progress_bar)

            layout.addLayout(button_layout)
        except Exception as e:
            logger.error(f"添加控制按钮失败: {e}")

    def _add_status_indicators(self, layout):
        """添加状态指示器"""
        try:
            # 连接状态
            self.connection_status_label = QLabel(self.lang_manager.get_text('indicator_not_connected'))
            self.connection_status_label.setStyleSheet("""
                background: #2a2a2a; 
                color: #FF4545; 
                padding: 12px; 
                border: 1px solid #FF4545; 
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
            """)
            layout.addWidget(self.connection_status_label)

            # 状态显示
            self.status_label = QLabel(f"{self.lang_manager.get_text('status_ready')}")
            self.status_label.setStyleSheet("""
                background: #2a2a2a; 
                color: #00FF7F; 
                padding: 12px; 
                border: 1px solid #00FF7F; 
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
            """)
            layout.addWidget(self.status_label)

            # 调试信息
            self.debug_label = QLabel("调试: 等待开始")
            self.debug_label.setStyleSheet("""
                background: #2a2a2a; 
                color: #FFD700; 
                padding: 10px; 
                border: 1px solid #FFD700; 
                border-radius: 8px;
                font-size: 12px;
                font-family: 'Consolas', monospace;
            """)
            layout.addWidget(self.debug_label)
        except Exception as e:
            logger.error(f"添加状态指示器失败: {e}")

    def _change_ui_language(self):
        """切换界面语言 - 实时切换"""
        try:
            selected_text = self.ui_language_combo.currentText()
            new_language = None

            # 找到对应的语言代码
            for lang_code, lang_name in self.lang_manager.languages.items():
                if lang_name == selected_text:
                    new_language = lang_code
                    break

            if new_language and new_language != self.lang_manager.current_language:
                # 设置新语言
                self.lang_manager.set_language(new_language)

                # 实时更新界面文本
                self._update_all_ui_texts()

                # 保存语言设置
                self._save_current_config()

                # 显示状态信息
                self._update_status(self.lang_manager.get_text('status_language_changed'), "#00FF7F")

        except Exception as e:
            logger.error(f"切换界面语言失败: {e}")

    def _update_all_ui_texts(self):
        """更新所有界面文本 - 实时切换语言"""
        try:
            # 更新窗口标题
            self.setWindowTitle(self.lang_manager.get_text('window_title'))

            # 更新主标题和广告
            if hasattr(self, 'title_label'):
                self.title_label.setText(self.lang_manager.get_text('main_title'))
            if hasattr(self, 'ad_label'):
                self.ad_label.setText(self.lang_manager.get_text('tech_support'))

            # 更新标签页标题
            if hasattr(self, 'tab_widget'):
                self.tab_widget.setTabText(0, self.lang_manager.get_text('tab_basic'))
                self.tab_widget.setTabText(1, self.lang_manager.get_text('tab_realtime'))
                self.tab_widget.setTabText(2, self.lang_manager.get_text('tab_hotwords'))
                self.tab_widget.setTabText(3, self.lang_manager.get_text('tab_advanced'))

            # 更新基本设置标签页
            if hasattr(self, 'language_label'):
                self.language_label.setText(self.lang_manager.get_text('label_language'))
            if hasattr(self, 'api_group'):
                self.api_group.setTitle(self.lang_manager.get_text('group_api'))
            if hasattr(self, 'api_key_label'):
                self.api_key_label.setText(self.lang_manager.get_text('label_api_key'))
            if hasattr(self, 'endpoint_label'):
                self.endpoint_label.setText(self.lang_manager.get_text('label_endpoint'))
            if hasattr(self, 'model_label'):
                self.model_label.setText(self.lang_manager.get_text('label_model'))
            if hasattr(self, 'language_model_label'):
                self.language_model_label.setText(self.lang_manager.get_text('label_language_model'))
            if hasattr(self, 'device_group'):
                self.device_group.setTitle(self.lang_manager.get_text('group_device'))
            if hasattr(self, 'device_label'):
                self.device_label.setText(self.lang_manager.get_text('label_device'))
            if hasattr(self, 'refresh_btn'):
                self.refresh_btn.setText(self.lang_manager.get_text('btn_refresh'))
            if hasattr(self, 'prompt_group'):
                self.prompt_group.setTitle(self.lang_manager.get_text('group_prompt'))
            if hasattr(self, 'prompt_help_label'):
                self.prompt_help_label.setText(self.lang_manager.get_text('help_prompt'))

            # 更新占位符文本
            if hasattr(self, 'api_key_input'):
                self.api_key_input.setPlaceholderText(self.lang_manager.get_text('placeholder_api_key'))
            if hasattr(self, 'prompt_text'):
                self.prompt_text.setPlaceholderText(self.lang_manager.get_text('placeholder_prompt'))

            # 更新预设按钮
            if hasattr(self, 'general_prompt_btn'):
                self.general_prompt_btn.setText(self.lang_manager.get_text('btn_general'))
            if hasattr(self, 'tech_prompt_btn'):
                self.tech_prompt_btn.setText(self.lang_manager.get_text('btn_tech'))
            if hasattr(self, 'business_prompt_btn'):
                self.business_prompt_btn.setText(self.lang_manager.get_text('btn_business'))
            if hasattr(self, 'medical_prompt_btn'):
                self.medical_prompt_btn.setText(self.lang_manager.get_text('btn_medical'))
            if hasattr(self, 'clear_prompt_btn'):
                self.clear_prompt_btn.setText(self.lang_manager.get_text('btn_clear'))

            # 更新实时设置标签页
            if hasattr(self, 'vad_group'):
                self.vad_group.setTitle(self.lang_manager.get_text('group_vad'))
            if hasattr(self, 'sensitivity_label'):
                self.sensitivity_label.setText(self.lang_manager.get_text('label_sensitivity'))
            if hasattr(self, 'silence_interval_label'):
                self.silence_interval_label.setText(self.lang_manager.get_text('label_silence_interval'))
            if hasattr(self, 'audio_group'):
                self.audio_group.setTitle(self.lang_manager.get_text('group_audio_enhance'))
            if hasattr(self, 'audio_filter_checkbox'):
                self.audio_filter_checkbox.setText(self.lang_manager.get_text('checkbox_audio_filter'))
            if hasattr(self, 'noise_gate_checkbox'):
                self.noise_gate_checkbox.setText(self.lang_manager.get_text('checkbox_noise_gate'))
            if hasattr(self, 'noise_reduction_label'):
                self.noise_reduction_label.setText(self.lang_manager.get_text('label_noise_reduction'))
            if hasattr(self, 'typewriter_group'):
                self.typewriter_group.setTitle(self.lang_manager.get_text('group_display'))
            if hasattr(self, 'line_break_label'):
                self.line_break_label.setText(self.lang_manager.get_text('label_line_break'))
            if hasattr(self, 'typing_speed_label'):
                self.typing_speed_label.setText(self.lang_manager.get_text('label_typing_speed'))

            # 更新热词标签页
            if hasattr(self, 'hotwords_group'):
                self.hotwords_group.setTitle(self.lang_manager.get_text('group_hotwords'))
            if hasattr(self, 'hotwords_help_label'):
                self.hotwords_help_label.setText(self.lang_manager.get_text('help_hotwords'))
            if hasattr(self, 'hotwords_text'):
                self.hotwords_text.setPlaceholderText(self.lang_manager.get_text('placeholder_hotwords'))
            if hasattr(self, 'ai_btn'):
                self.ai_btn.setText(self.lang_manager.get_text('btn_ai_words'))
            if hasattr(self, 'tech_btn'):
                self.tech_btn.setText(self.lang_manager.get_text('btn_tech_words'))
            if hasattr(self, 'business_btn'):
                self.business_btn.setText(self.lang_manager.get_text('btn_business_words'))
            if hasattr(self, 'medical_btn'):
                self.medical_btn.setText(self.lang_manager.get_text('btn_medical_words'))
            if hasattr(self, 'edu_btn'):
                self.edu_btn.setText(self.lang_manager.get_text('btn_edu_words'))
            if hasattr(self, 'clear_hotwords_btn'):
                self.clear_hotwords_btn.setText(self.lang_manager.get_text('btn_clear'))
            if hasattr(self, 'usage_group'):
                self.usage_group.setTitle(self.lang_manager.get_text('group_usage'))
            if hasattr(self, 'usage_text'):
                self.usage_text.setText(self.lang_manager.get_text('usage_text'))

            # 更新高级设置标签页
            if hasattr(self, 'network_group'):
                self.network_group.setTitle(self.lang_manager.get_text('group_network'))
            if hasattr(self, 'timeout_label'):
                self.timeout_label.setText(self.lang_manager.get_text('label_timeout'))
            if hasattr(self, 'reconnect_label'):
                self.reconnect_label.setText(self.lang_manager.get_text('label_reconnect'))
            if hasattr(self, 'perf_group'):
                self.perf_group.setTitle(self.lang_manager.get_text('group_performance'))
            if hasattr(self, 'ultra_mode_checkbox'):
                self.ultra_mode_checkbox.setText(self.lang_manager.get_text('checkbox_ultra_mode'))
            if hasattr(self, 'aggressive_cleanup_checkbox'):
                self.aggressive_cleanup_checkbox.setText(self.lang_manager.get_text('checkbox_aggressive_cleanup'))
            if hasattr(self, 'debug_group'):
                self.debug_group.setTitle(self.lang_manager.get_text('group_debug'))
            if hasattr(self, 'debug_mode_checkbox'):
                self.debug_mode_checkbox.setText(self.lang_manager.get_text('checkbox_debug_mode'))

            # 更新控制按钮
            if hasattr(self, 'start_button'):
                self.start_button.setText(self.lang_manager.get_text('btn_start'))
            if hasattr(self, 'stop_button'):
                self.stop_button.setText(self.lang_manager.get_text('btn_stop'))
            if hasattr(self, 'clear_button'):
                self.clear_button.setText(self.lang_manager.get_text('btn_clear'))
            if hasattr(self, 'save_button'):
                self.save_button.setText(self.lang_manager.get_text('btn_save'))
            if hasattr(self, 'load_file_button'):
                self.load_file_button.setText(self.lang_manager.get_text('btn_load_file'))
            if hasattr(self, 'copy_button'):
                self.copy_button.setText(self.lang_manager.get_text('btn_copy'))
            if hasattr(self, 'export_button'):
                self.export_button.setText(self.lang_manager.get_text('btn_export'))
            if hasattr(self, 'settings_button'):
                self.settings_button.setText(self.lang_manager.get_text('btn_settings'))

            # 更新音频监控面板
            if hasattr(self, 'audio_title'):
                self.audio_title.setText(self.lang_manager.get_text('audio_monitor_title'))
            if hasattr(self, 'wave_label'):
                self.wave_label.setText(self.lang_manager.get_text('audio_waveform'))
            if hasattr(self, 'volume_label'):
                self.volume_label.setText(self.lang_manager.get_text('audio_volume'))
            if hasattr(self, 'stats_label'):
                self.stats_label.setText(self.lang_manager.get_text('audio_stats'))

            # 更新字幕显示区域
            if hasattr(self, 'subtitle_title'):
                self.subtitle_title.setText(self.lang_manager.get_text('subtitle_title'))
            if hasattr(self, 'auto_scroll_btn'):
                self.auto_scroll_btn.setText(self.lang_manager.get_text('btn_auto_scroll'))
            if hasattr(self, 'font_size_btn'):
                self.font_size_btn.setText(self.lang_manager.get_text('btn_font'))
            if hasattr(self, 'realtime_indicator'):
                self.realtime_indicator.setText(self.lang_manager.get_text('indicator_ready'))
            if hasattr(self, 'format_label'):
                self.format_label.setText(self.lang_manager.get_text('subtitle_format'))

            # 更新语言下拉框选项
            if hasattr(self, 'language_combo'):
                self.language_combo.clear()
                languages = [
                    ('auto', self.lang_manager.get_text('language_auto')),
                    ('zh', self.lang_manager.get_text('language_chinese')),
                    ('en', self.lang_manager.get_text('language_english')),
                    ('ja', self.lang_manager.get_text('language_japanese')),
                    ('ko', self.lang_manager.get_text('language_korean')),
                    ('fr', self.lang_manager.get_text('language_french')),
                    ('de', self.lang_manager.get_text('language_german')),
                    ('es', self.lang_manager.get_text('language_spanish')),
                    ('it', self.lang_manager.get_text('language_italian')),
                    ('pt', self.lang_manager.get_text('language_portuguese')),
                    ('ru', self.lang_manager.get_text('language_russian')),
                    ('ar', self.lang_manager.get_text('language_arabic')),
                    ('hi', self.lang_manager.get_text('language_hindi')),
                    ('th', self.lang_manager.get_text('language_thai')),
                    ('vi', self.lang_manager.get_text('language_vietnamese'))
                ]
                for code, name in languages:
                    self.language_combo.addItem(name, code)

            # 更新数值标签（使用当前值重新格式化）
            self._update_numeric_labels()

        except Exception as e:
            logger.error(f"更新界面文本失败: {e}")

    def _update_numeric_labels(self):
        """更新数值标签（重新格式化单位文本）"""
        try:
            # 更新滑块标签的单位
            if hasattr(self, 'silence_duration_slider') and hasattr(self, 'silence_duration_label'):
                value = self.silence_duration_slider.value()
                self.silence_duration_label.setText(f"{value}{self.lang_manager.get_text('unit_ms')}")

            if hasattr(self, 'noise_reduction_slider') and hasattr(self, 'noise_reduction_display_label'):
                value = self.noise_reduction_slider.value()
                self.noise_reduction_display_label.setText(f"{value}{self.lang_manager.get_text('unit_percent')}")

            if hasattr(self, 'line_break_slider') and hasattr(self, 'line_break_display_label'):
                value = self.line_break_slider.value()
                self.line_break_display_label.setText(f"{value}{self.lang_manager.get_text('unit_sentences')}")

            if hasattr(self, 'typewriter_speed_slider') and hasattr(self, 'typewriter_speed_display_label'):
                value = self.typewriter_speed_slider.value()
                self.typewriter_speed_display_label.setText(f"{value}{self.lang_manager.get_text('unit_ms_per_char')}")

            if hasattr(self, 'timeout_slider') and hasattr(self, 'timeout_display_label'):
                value = self.timeout_slider.value()
                self.timeout_display_label.setText(f"{value}{self.lang_manager.get_text('unit_seconds')}")

            if hasattr(self, 'reconnect_slider') and hasattr(self, 'reconnect_display_label'):
                value = self.reconnect_slider.value()
                self.reconnect_display_label.setText(f"{value}{self.lang_manager.get_text('unit_times')}")

            # 更新音频监控标签
            if hasattr(self, 'peak_level_label'):
                peak_percent = int(getattr(self.volume_indicator, 'peak_level', 0) * 100)
                self.peak_level_label.setText(f"{self.lang_manager.get_text('audio_peak')}: {peak_percent}%")

            if hasattr(self, 'total_chars_label'):
                self.total_chars_label.setText(f"{self.lang_manager.get_text('audio_chars')}: {self.total_chars}")

            if hasattr(self, 'avg_speed_label'):
                # 重新计算并格式化速度标签
                if self.session_start_time:
                    elapsed = time.time() - self.session_start_time
                    if elapsed > 0:
                        chars_per_minute = int((self.total_chars * 60) / elapsed)
                        self.avg_speed_label.setText(
                            f"{chars_per_minute} {self.lang_manager.get_text('unit_chars_per_min')}")

            # 更新字幕显示区域标签
            if hasattr(self, 'word_count_label'):
                word_count = 0
                if hasattr(self, 'typewriter_display'):
                    text_content = self.typewriter_display.toPlainText()
                    word_count = len(text_content.replace('\n', '').replace(' ', ''))
                self.word_count_label.setText(f"{self.lang_manager.get_text('subtitle_word_count')}: {word_count}")

            if hasattr(self, 'typewriter_count_label'):
                typewriter_count = 0
                if hasattr(self, 'typewriter_display'):
                    typewriter_count = len(self.typewriter_display.typewriter_items)
                self.typewriter_count_label.setText(
                    f"{self.lang_manager.get_text('subtitle_active_items')}: {typewriter_count}")

            if hasattr(self, 'delay_indicator'):
                self.delay_indicator.setText(f"{self.lang_manager.get_text('subtitle_delay')}: <20ms")

        except Exception as e:
            logger.error(f"更新数值标签失败: {e}")

    def load_audio_devices(self):
        """加载音频设备"""
        try:
            if not hasattr(self, 'device_combo'):
                return

            recorder = UltraFastAudioRecorder(self.current_config)
            self.audio_devices = recorder.get_available_devices()
            recorder.close()

            self.device_combo.clear()
            for device in self.audio_devices:
                display_name = f"{device['name'][:40]}..."
                self.device_combo.addItem(display_name, device['index'])

            self._update_status(self.lang_manager.get_text('status_device_updated'), "#00FF7F")

        except Exception as e:
            error_msg = f"设备加载失败: {str(e)}"
            logger.error(error_msg)
            self._update_status("❌ 设备加载失败", "#FF4545")

    def _update_config(self):
        """更新配置"""
        try:
            self.current_config.update({
                'model': getattr(self, 'model_combo', None) and self.model_combo.currentText() or 'gpt-4o-transcribe',
                'language': getattr(self, 'language_combo', None) and (
                        self.language_combo.currentData() or self.language_combo.currentText()) or 'zh',
                'prompt': getattr(self, 'prompt_text', None) and self.prompt_text.toPlainText() or '',
                'device_index': getattr(self, 'device_combo', None) and self.device_combo.currentData() or None,
                'base_url': getattr(self, 'base_url_input',
                                    None) and self.base_url_input.text().strip() or 'https://api.openai.com/v1',
                'api_key': getattr(self, 'api_key_input', None) and self.api_key_input.text().strip() or '',
                'use_streaming': True,
                'audio_filter_enabled': getattr(self, 'audio_filter_checkbox',
                                                None) and self.audio_filter_checkbox.isChecked() or True,
                'noise_gate_enabled': getattr(self, 'noise_gate_checkbox',
                                              None) and self.noise_gate_checkbox.isChecked() or True,
                'ultra_mode': getattr(self, 'ultra_mode_checkbox',
                                      None) and self.ultra_mode_checkbox.isChecked() or True,
                'aggressive_cleanup': getattr(self, 'aggressive_cleanup_checkbox',
                                              None) and self.aggressive_cleanup_checkbox.isChecked() or True,
                'debug_mode': getattr(self, 'debug_mode_checkbox',
                                      None) and self.debug_mode_checkbox.isChecked() or False,
                'output_format': 'text'
            })
        except Exception as e:
            logger.error(f"更新配置失败: {e}")

    def _update_vad_threshold(self, value):
        """更新VAD阈值"""
        try:
            threshold = value / 100.0
            self.current_config['vad_threshold'] = threshold
            if hasattr(self, 'vad_label'):
                self.vad_label.setText(f"{threshold:.2f}")
        except Exception as e:
            logger.error(f"更新VAD阈值失败: {e}")

    def _update_silence_duration(self, value):
        """更新静音持续时间"""
        try:
            self.current_config['silence_duration_ms'] = value
            if hasattr(self, 'silence_duration_label'):
                self.silence_duration_label.setText(f"{value}{self.lang_manager.get_text('unit_ms')}")
        except Exception as e:
            logger.error(f"更新静音持续时间失败: {e}")

    def _update_noise_reduction(self, value):
        """更新噪音抑制级别"""
        try:
            level = value / 100.0
            self.current_config['noise_reduction_level'] = level
            if hasattr(self, 'noise_reduction_display_label'):
                self.noise_reduction_display_label.setText(f"{value}{self.lang_manager.get_text('unit_percent')}")
        except Exception as e:
            logger.error(f"更新噪音抑制级别失败: {e}")

    def _update_line_break_interval(self, value):
        """更新换行间隔"""
        try:
            if hasattr(self, 'line_break_display_label'):
                self.line_break_display_label.setText(f"{value}{self.lang_manager.get_text('unit_sentences')}")
            # 如果有转录线程在运行，更新其设置
            if self.transcription_thread and hasattr(self.transcription_thread, 'asr_manager'):
                self.transcription_thread.asr_manager.line_break_interval = value
        except Exception as e:
            logger.error(f"更新换行间隔失败: {e}")

    def _update_typewriter_speed(self, value):
        """更新打字机速度"""
        try:
            self.current_config['typewriter_speed_ms'] = value
            if hasattr(self, 'typewriter_speed_display_label'):
                self.typewriter_speed_display_label.setText(f"{value}{self.lang_manager.get_text('unit_ms_per_char')}")

            # 更新打字机定时器
            if hasattr(self, 'typewriter_display'):
                self.typewriter_display.typewriter_timer.stop()
                self.typewriter_display.typewriter_timer.start(value)
        except Exception as e:
            logger.error(f"更新打字机速度失败: {e}")

    def _update_timeout(self, value):
        """更新连接超时"""
        try:
            self.current_config['connection_timeout'] = value
            if hasattr(self, 'timeout_display_label'):
                self.timeout_display_label.setText(f"{value}{self.lang_manager.get_text('unit_seconds')}")
        except Exception as e:
            logger.error(f"更新连接超时失败: {e}")

    def _update_reconnect(self, value):
        """更新重连次数"""
        try:
            self.current_config['max_reconnect_attempts'] = value
            if hasattr(self, 'reconnect_display_label'):
                self.reconnect_display_label.setText(f"{value}{self.lang_manager.get_text('unit_times')}")
        except Exception as e:
            logger.error(f"更新重连次数失败: {e}")

    def _add_preset_hotwords(self, words):
        """添加预设热词"""
        try:
            if not hasattr(self, 'hotwords_text'):
                return

            current_text = self.hotwords_text.toPlainText().strip()
            if current_text:
                current_text += "\n"
            current_text += "\n".join(words)
            self.hotwords_text.setPlainText(current_text)
        except Exception as e:
            logger.error(f"添加预设热词失败: {e}")

    def _update_hotwords(self):
        """更新热词配置"""
        try:
            if not hasattr(self, 'hotwords_text'):
                return

            text = self.hotwords_text.toPlainText().strip()
            hotwords = [line.strip() for line in text.split('\n') if line.strip()]
            self.current_config['hotwords'] = hotwords
        except Exception as e:
            logger.error(f"更新热词配置失败: {e}")

    def _update_displays(self):
        """更新显示信息"""
        try:
            # 更新音量显示
            if hasattr(self, 'volume_indicator') and self.volume_indicator:
                volume_percent = int(self.volume_indicator.volume_level * 100)
                peak_percent = int(self.volume_indicator.peak_level * 100)

                if hasattr(self, 'volume_level_label'):
                    self.volume_level_label.setText(f"{volume_percent}%")
                if hasattr(self, 'peak_level_label'):
                    self.peak_level_label.setText(f"{self.lang_manager.get_text('audio_peak')}: {peak_percent}%")

                if volume_percent < 3:
                    noise_level = self.lang_manager.get_text('audio_quiet')
                    noise_color = "#00FF7F"
                elif volume_percent < 15:
                    noise_level = self.lang_manager.get_text('audio_normal')
                    noise_color = "#FFD700"
                else:
                    noise_level = self.lang_manager.get_text('audio_noisy')
                    noise_color = "#FF4545"

                if hasattr(self, 'noise_level_label'):
                    self.noise_level_label.setText(noise_level)
                    self.noise_level_label.setStyleSheet(f"font-size: 10px; color: {noise_color};")

            # 更新会话统计
            if self.session_start_time:
                elapsed = time.time() - self.session_start_time
                hours = int(elapsed // 3600)
                minutes = int((elapsed % 3600) // 60)
                seconds = int(elapsed % 60)

                if hasattr(self, 'session_time_label'):
                    self.session_time_label.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
                if hasattr(self, 'total_chars_label'):
                    self.total_chars_label.setText(f"{self.lang_manager.get_text('audio_chars')}: {self.total_chars}")

                if elapsed > 0:
                    chars_per_minute = int((self.total_chars * 60) / elapsed)
                    if hasattr(self, 'avg_speed_label'):
                        self.avg_speed_label.setText(
                            f"{chars_per_minute} {self.lang_manager.get_text('unit_chars_per_min')}")

            # 更新调试信息
            if self.transcription_thread:
                audio_sent = getattr(self.transcription_thread, 'audio_chunks_sent', 0)
                msgs_received = getattr(self.transcription_thread, 'messages_received', 0)
                if hasattr(self, 'debug_label'):
                    self.debug_label.setText(f"音频块:{audio_sent} 消息:{msgs_received}")

            # 更新字数统计
            if hasattr(self, 'typewriter_display'):
                text_content = self.typewriter_display.toPlainText()
                word_count = len(text_content.replace('\n', '').replace(' ', ''))
                if hasattr(self, 'word_count_label'):
                    self.word_count_label.setText(f"{self.lang_manager.get_text('subtitle_word_count')}: {word_count}")

                # 更新活跃项目计数
                typewriter_count = len(self.typewriter_display.typewriter_items)
                if hasattr(self, 'typewriter_count_label'):
                    self.typewriter_count_label.setText(
                        f"{self.lang_manager.get_text('subtitle_active_items')}: {typewriter_count}")

                # 动态延迟显示
                if typewriter_count > 0:
                    if hasattr(self, 'delay_indicator'):
                        self.delay_indicator.setText(f"{self.lang_manager.get_text('subtitle_delay')}: <15ms")
                    if hasattr(self, 'typing_indicator'):
                        self.typing_indicator.setText(self.lang_manager.get_text('indicator_typing'))
                        self.typing_indicator.setStyleSheet("color: #00FF7F; font-size: 13px; font-weight: bold;")
                else:
                    if hasattr(self, 'delay_indicator'):
                        self.delay_indicator.setText(f"{self.lang_manager.get_text('subtitle_delay')}: <20ms")
                    if hasattr(self, 'typing_indicator'):
                        self.typing_indicator.setText(self.lang_manager.get_text('indicator_waiting'))
                        self.typing_indicator.setStyleSheet("color: #888888; font-size: 13px; font-weight: bold;")

        except Exception as e:
            logger.error(f"更新显示信息失败: {e}")

    def start_transcription(self):
        """开始实时转录"""
        try:
            api_key = getattr(self, 'api_key_input', None) and self.api_key_input.text().strip()
            if not api_key:
                self._update_status(self.lang_manager.get_text('status_api_key_required'), "#FF4545")
                QMessageBox.warning(self,
                                    self.lang_manager.get_text('dialog_config_error'),
                                    self.lang_manager.get_text('dialog_api_key_required'))
                return

            self._update_config()

            # 重置统计
            self.total_chars = 0
            self.session_start_time = time.time()
            self.error_count = 0

            # 清空显示
            if QMessageBox.question(self,
                                    self.lang_manager.get_text('dialog_start_transcription'),
                                    self.lang_manager.get_text('dialog_clear_content')) == QMessageBox.Yes:
                if hasattr(self, 'typewriter_display'):
                    self.typewriter_display.clear()
                    self.typewriter_display.clear_all_typewriter()

            # 更新指示器
            if hasattr(self, 'realtime_indicator'):
                self.realtime_indicator.setText(self.lang_manager.get_text('indicator_active'))
                self.realtime_indicator.setStyleSheet("""
                    color: #00FF7F; 
                    font-weight: bold; 
                    font-size: 15px;
                    padding: 8px 15px;
                    background: rgba(0, 255, 127, 0.1);
                    border-radius: 8px;
                    border: 1px solid #00FF7F;
                """)

            # 启动音频可视化
            if hasattr(self, 'audio_visualizer') and self.audio_visualizer:
                self.audio_visualizer.start_recording()

            # 创建实时转录线程
            self.transcription_thread = UltraRealtimeTranscriber(self.current_config)
            if hasattr(self, 'audio_visualizer') and hasattr(self, 'volume_indicator'):
                self.transcription_thread.set_visualizers(self.audio_visualizer, self.volume_indicator)

            # 连接信号 - 修复参数问题
            self.transcription_thread.typewriter_delta.connect(self._handle_typewriter_delta)
            self.transcription_thread.typewriter_completed.connect(self._handle_typewriter_completed)
            self.transcription_thread.speech_committed.connect(self._handle_speech_committed)
            self.transcription_thread.error_occurred.connect(self.handle_error)
            self.transcription_thread.status_update.connect(self._update_status)
            self.transcription_thread.connection_status.connect(self._update_connection_status)

            # 启动转录
            self.transcription_thread.start()

            # 更新界面状态
            self._set_transcription_state(True)
            self._update_status(self.lang_manager.get_text('status_starting'), "#00FF7F")

        except Exception as e:
            error_msg = f"启动实时转录失败: {str(e)}"
            logger.error(error_msg)
            self.handle_error(error_msg)

    def _handle_typewriter_delta(self, item_id, delta_text, full_text, displayed_length, new_chars_count):
        """处理打字机增量信号"""
        try:
            self.total_chars += len(delta_text)

            # 添加到打字机显示组件
            if hasattr(self, 'typewriter_display'):
                self.typewriter_display.add_typewriter_text(item_id, delta_text, full_text, displayed_length,
                                                            new_chars_count)

            logger.debug(
                f"⚡ 增量 [{item_id}]: '{delta_text}' -> '{full_text}' (显示:{displayed_length}, 新增:{new_chars_count})")

        except Exception as e:
            logger.error(f"处理打字机增量失败: {e}")

    def _handle_typewriter_completed(self, item_id, final_text, previous_text, should_break_line):
        """处理打字机完成信号"""
        try:
            # 完成打字机项目
            if hasattr(self, 'typewriter_display'):
                self.typewriter_display.finalize_typewriter_item(item_id, final_text, previous_text, should_break_line)

            logger.debug(f"✅ 完成 [{item_id}]: '{final_text}' (换行: {should_break_line})")

            # 保存到历史记录
            self.subtitle_history.append({
                'text': final_text,
                'timestamp': time.strftime("%H:%M:%S"),
                'metadata': {
                    'source': 'realtime_typewriter',
                    'item_id': item_id,
                    'previous_text': previous_text,
                    'should_break_line': should_break_line
                }
            })

        except Exception as e:
            logger.error(f"处理打字机完成失败: {e}")

    def _handle_speech_committed(self, item_id, previous_item_id):
        """处理语音提交信号"""
        try:
            logger.debug(f"⚡ 语音已提交 [{item_id}] (前一个: {previous_item_id})")
        except Exception as e:
            logger.error(f"处理语音提交失败: {e}")

    def stop_transcription(self):
        """停止实时转录"""
        try:
            if self.transcription_thread:
                self.transcription_thread.stop_transcription()
                self.transcription_thread.wait(5000)
                self.transcription_thread = None

            if hasattr(self, 'audio_visualizer') and self.audio_visualizer:
                self.audio_visualizer.stop_recording()

            # 重置指示器
            if hasattr(self, 'realtime_indicator'):
                self.realtime_indicator.setText(self.lang_manager.get_text('indicator_stopped'))
                self.realtime_indicator.setStyleSheet("""
                    color: #FF4545; 
                    font-weight: bold; 
                    font-size: 15px;
                    padding: 8px 15px;
                    background: rgba(255, 69, 0, 0.1);
                    border-radius: 8px;
                    border: 1px solid #FF4545;
                """)

            # 清除打字机记录
            if hasattr(self, 'typewriter_display'):
                self.typewriter_display.clear_all_typewriter()

            self._set_transcription_state(False)
            self._update_status(self.lang_manager.get_text('status_stopped'), "#FFD700")
            self._update_connection_status(self.lang_manager.get_text('indicator_not_connected'), "#FF4545")

        except Exception as e:
            error_msg = f"停止转录失败: {str(e)}"
            logger.error(error_msg)

    def clear_display(self):
        """清空显示"""
        try:
            if QMessageBox.question(self,
                                    self.lang_manager.get_text('dialog_clear_confirm'),
                                    self.lang_manager.get_text('dialog_clear_all')) == QMessageBox.Yes:
                if hasattr(self, 'typewriter_display'):
                    self.typewriter_display.clear()
                    self.typewriter_display.clear_all_typewriter()
                self.subtitle_history.clear()
                self.total_chars = 0
                self._update_status(self.lang_manager.get_text('status_cleared'), "#00FF7F")
        except Exception as e:
            logger.error(f"清空显示失败: {e}")

    def save_transcription(self):
        """保存转录结果"""
        try:
            has_content = (
                                  hasattr(self, 'typewriter_display') and
                                  self.typewriter_display.toPlainText().strip()
                          ) or self.subtitle_history

            if not has_content:
                self._update_status(self.lang_manager.get_text('status_no_content'), "#FF4545")
                QMessageBox.information(self,
                                        self.lang_manager.get_text('dialog_tip'),
                                        self.lang_manager.get_text('dialog_no_content_save'))
                return

            file_path, _ = QFileDialog.getSaveFileName(
                self, self.lang_manager.get_text('file_save_transcription'),
                f"realtime_asr_{time.strftime('%Y%m%d_%H%M%S')}.txt",
                f"{self.lang_manager.get_text('file_text_files')};;{self.lang_manager.get_text('file_all_files')}"
            )

            if file_path:
                content = ""
                if hasattr(self, 'typewriter_display'):
                    content = self.typewriter_display.toPlainText()

                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                self._update_status(self.lang_manager.get_text('status_saved'), "#00FF7F")
                QMessageBox.information(self,
                                        self.lang_manager.get_text('dialog_save_success'),
                                        f"{self.lang_manager.get_text('dialog_save_to')}:\n{file_path}")

        except Exception as e:
            error_msg = f"保存失败: {str(e)}"
            logger.error(error_msg)
            self.handle_error(error_msg)

    def load_audio_file(self):
        """加载音频文件进行转录"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, self.lang_manager.get_text('file_select_audio'), "",
                f"{self.lang_manager.get_text('file_audio_files')};;{self.lang_manager.get_text('file_all_files')}"
            )

            if file_path:
                self._transcribe_audio_file(file_path)
        except Exception as e:
            logger.error(f"加载音频文件失败: {e}")

    def _transcribe_audio_file(self, file_path):
        """转录音频文件"""
        try:
            api_key = getattr(self, 'api_key_input', None) and self.api_key_input.text().strip()
            if not api_key:
                self._update_status(self.lang_manager.get_text('status_api_key_required'), "#FF4545")
                return

            self._update_config()

            # 显示进度条
            if hasattr(self, 'progress_bar'):
                self.progress_bar.setVisible(True)
                self.progress_bar.setValue(0)

            # 创建文件转录工作线程
            self.file_transcription_worker = FileTranscriptionWorker(
                file_path, self.current_config, 'text'
            )

            # 连接信号
            if hasattr(self, 'progress_bar'):
                self.file_transcription_worker.progress_update.connect(self.progress_bar.setValue)
            self.file_transcription_worker.transcription_ready.connect(self._handle_file_transcription)
            self.file_transcription_worker.error_occurred.connect(self.handle_error)
            self.file_transcription_worker.status_update.connect(self._update_status)
            self.file_transcription_worker.finished.connect(self._file_transcription_finished)

            # 启动转录
            self.file_transcription_worker.start()

            # 禁用相关按钮
            if hasattr(self, 'load_file_button'):
                self.load_file_button.setEnabled(False)
            if hasattr(self, 'start_button'):
                self.start_button.setEnabled(False)

        except Exception as e:
            error_msg = f"文件转录失败: {str(e)}"
            logger.error(error_msg)
            self.handle_error(error_msg)

    def _handle_file_transcription(self, text, timestamp, metadata):
        """处理文件转录结果"""
        try:
            if not hasattr(self, 'typewriter_display'):
                return

            cursor = self.typewriter_display.textCursor()
            cursor.movePosition(QTextCursor.End)

            # 文件来源显示
            source_text = "文件转录"
            if metadata.get('source') == 'file_large_split':
                source_text = f"大文件转录 (分{metadata.get('chunks_count', 0)}块)"

            file_html = f"""
            <div style='color: #CCCCCC; background: rgba(255, 215, 0, 0.1); padding: 12px; 
                        border-left: 4px solid #FFD700; border-radius: 8px; margin: 8px 0;'>
                <div style='color: #FFD700; font-size: 14px; margin-bottom: 6px; font-weight: bold;'>
                    📁 [{source_text}] {timestamp}
                </div>
                <div style='color: #CCCCCC; font-size: 18px; line-height: 2.0;'>
                    {text}
                </div>
            </div><br>
            """

            cursor.insertHtml(file_html)
            self.typewriter_display._auto_scroll()

            # 添加到历史记录
            self.subtitle_history.append({
                'text': text,
                'timestamp': timestamp,
                'metadata': metadata
            })

        except Exception as e:
            logger.error(f"处理文件转录结果失败: {e}")

    def _file_transcription_finished(self):
        """文件转录完成"""
        try:
            if hasattr(self, 'progress_bar'):
                self.progress_bar.setVisible(False)
            if hasattr(self, 'load_file_button'):
                self.load_file_button.setEnabled(True)
            if hasattr(self, 'start_button'):
                self.start_button.setEnabled(True)
            self.file_transcription_worker = None
        except Exception as e:
            logger.error(f"文件转录完成处理失败: {e}")

    def _copy_transcription(self):
        """复制转录内容"""
        try:
            content = ""
            if hasattr(self, 'typewriter_display'):
                content = self.typewriter_display.toPlainText()

            if content.strip():
                clipboard = QApplication.clipboard()
                clipboard.setText(content)
                self._update_status(self.lang_manager.get_text('status_copied'), "#00FF7F")
            else:
                self._update_status(self.lang_manager.get_text('status_no_content'), "#FF4545")
        except Exception as e:
            logger.error(f"复制转录内容失败: {e}")

    def _export_transcription(self):
        """导出转录内容"""
        self.save_transcription()

    def _open_settings(self):
        """打开设置对话框"""
        QMessageBox.information(self,
                                self.lang_manager.get_text('dialog_settings'),
                                self.lang_manager.get_text('dialog_settings_info'))

    def _adjust_font_size(self):
        """调整字体大小"""
        try:
            if not hasattr(self, 'typewriter_display'):
                return

            current_font = self.typewriter_display.font()
            current_size = current_font.pointSize()

            sizes = [14, 16, 18, 20, 22, 24, 26]
            try:
                current_index = sizes.index(current_size)
                next_index = (current_index + 1) % len(sizes)
            except ValueError:
                next_index = 0

            new_size = sizes[next_index]
            current_font.setPointSize(new_size)
            self.typewriter_display.setFont(current_font)

            self._update_status(
                f"{self.lang_manager.get_text('status_font_size')}: {new_size}{self.lang_manager.get_text('unit_pt')}",
                "#00FF7F")

        except Exception as e:
            logger.error(f"调整字体大小失败: {e}")

    def _set_transcription_state(self, transcribing):
        """设置转录状态"""
        try:
            if hasattr(self, 'start_button'):
                self.start_button.setEnabled(not transcribing)
            if hasattr(self, 'stop_button'):
                self.stop_button.setEnabled(transcribing)

            # 禁用关键设置控件
            controls = []
            if hasattr(self, 'api_key_input'):
                controls.append(self.api_key_input)
            if hasattr(self, 'base_url_input'):
                controls.append(self.base_url_input)
            if hasattr(self, 'model_combo'):
                controls.append(self.model_combo)
            if hasattr(self, 'device_combo'):
                controls.append(self.device_combo)

            for control in controls:
                control.setEnabled(not transcribing)

        except Exception as e:
            logger.error(f"设置转录状态失败: {e}")

    def _update_status(self, message, color="#00FF7F"):
        """更新状态显示"""
        try:
            if hasattr(self, 'status_label'):
                self.status_label.setText(f"状态: {message}")
                self.status_label.setStyleSheet(f"""
                    background: #2a2a2a; 
                    color: {color}; 
                    padding: 12px; 
                    border: 1px solid {color}; 
                    border-radius: 8px;
                    font-weight: bold;
                    font-size: 14px;
                """)
        except Exception as e:
            logger.error(f"更新状态显示失败: {e}")

    def _update_connection_status(self, status, color):
        """更新连接状态"""
        try:
            if hasattr(self, 'connection_status_label'):
                self.connection_status_label.setText(status)
                self.connection_status_label.setStyleSheet(f"""
                    background: #2a2a2a; 
                    color: {color}; 
                    padding: 12px; 
                    border: 1px solid {color}; 
                    border-radius: 8px;
                    font-weight: bold;
                    font-size: 14px;
                """)
        except Exception as e:
            logger.error(f"更新连接状态失败: {e}")

    def handle_error(self, error_msg):
        """处理错误"""
        try:
            self._update_status(f"❌ {error_msg}", "#FF4545")
            logger.error(f"应用错误: {error_msg}")

            self.error_count += 1

            if "API" in error_msg or "认证" in error_msg or "授权" in error_msg:
                QMessageBox.critical(self,
                                     self.lang_manager.get_text('dialog_api_error'),
                                     error_msg)
            elif self.error_count <= 3:  # 只显示前3个错误，避免错误弹窗过多
                QMessageBox.warning(self,
                                    self.lang_manager.get_text('dialog_error'),
                                    error_msg)

        except Exception as e:
            logger.error(f"处理错误时出错: {e}")

    def _get_dark_theme(self):
        """获取暗黑主题样式"""
        return """
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #0a0a0a, stop:1 #1a1a1a);
                color: #E0E0E0;
            }

            QWidget {
                background-color: #1a1a1a;
                color: #E0E0E0;
                font-family: 'Microsoft YaHei', 'Segoe UI', sans-serif;
                font-size: 14px;
            }

            QFrame {
                background: #1a1a1a;
                border: 1px solid #404040;
                border-radius: 10px;
            }

            QGroupBox {
                font-weight: bold;
                border: 1px solid #404040;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 18px;
                background: #1a1a1a;
                color: #CCCCCC;
            }

            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px 0 8px;
                background: #1a1a1a;
                color: #00FF7F;
                font-size: 15px;
                font-weight: bold;
            }

            QPushButton {
                background: #FFD700;
                color: black;
                border: none;
                padding: 12px 18px;
                border-radius: 8px;
                font-size: 15px;
                font-weight: bold;
                min-height: 18px;
            }

            QPushButton:hover {
                background: #FFE033;
            }

            QPushButton:pressed {
                background: #E6C200;
            }

            QPushButton:disabled {
                background: #404040;
                color: #888888;
            }

            QPushButton:checked {
                background: #00FF7F;
                color: black;
            }

            QLineEdit, QTextEdit {
                padding: 10px;
                border: 1px solid #404040;
                border-radius: 8px;
                font-size: 15px;
                background: #2a2a2a;
                color: #E0E0E0;
                selection-background-color: #00FF7F;
                selection-color: #000000;
            }

            QLineEdit:focus, QTextEdit:focus {
                border-color: #00FF7F;
            }

            QComboBox {
                padding: 8px 12px;
                border: 1px solid #404040;
                border-radius: 8px;
                min-height: 25px;
                background: #2a2a2a;
                color: #E0E0E0;
                font-size: 15px;
            }

            QComboBox:focus {
                border-color: #00FF7F;
            }

            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left: 1px solid #404040;
            }

            QComboBox::down-arrow {
                image: none;
                border: none;
                width: 0;
                height: 0;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #888888;
            }

            QComboBox QAbstractItemView {
                border: 1px solid #404040;
                background: #2a2a2a;
                color: #E0E0E0;
                selection-background-color: #00FF7F;
                selection-color: #000000;
                font-size: 15px;
            }

            QCheckBox {
                spacing: 10px;
                color: #E0E0E0;
                font-size: 15px;
            }

            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid #404040;
                background: #2a2a2a;
            }

            QCheckBox::indicator:checked {
                background: #00FF7F;
                border-color: #00FF7F;
            }

            QSlider::groove:horizontal {
                border: 1px solid #404040;
                height: 8px;
                background: #2a2a2a;
                margin: 2px 0;
                border-radius: 4px;
            }

            QSlider::handle:horizontal {
                background: #00FF7F;
                border: 1px solid #00FF7F;
                width: 18px;
                margin: -6px 0;
                border-radius: 9px;
            }

            QSlider::handle:horizontal:hover {
                background: #00D966;
            }

            QScrollBar:vertical {
                background: #2a2a2a;
                width: 12px;
                border-radius: 6px;
            }

            QScrollBar::handle:vertical {
                background: #404040;
                border-radius: 6px;
                min-height: 20px;
            }

            QScrollBar::handle:vertical:hover {
                background: #505050;
            }

            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }

            QLabel {
                color: #E0E0E0;
                font-size: 15px;
            }

            QProgressBar {
                border: 2px solid #404040;
                border-radius: 8px;
                text-align: center;
                background: #2a2a2a;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 15px;
                height: 25px;
            }

            QProgressBar::chunk {
                background: #00FF7F;
                border-radius: 6px;
            }
        """

    def closeEvent(self, event):
        """关闭事件"""
        try:
            # 保存当前配置
            self._save_current_config()

            # 停止转录线程
            if self.transcription_thread:
                self.transcription_thread.stop_transcription()
                self.transcription_thread.wait(3000)

            # 停止文件转录线程
            if self.file_transcription_worker:
                self.file_transcription_worker.cancel()
                self.file_transcription_worker.wait(3000)

            # 停止音频可视化
            if hasattr(self, 'audio_visualizer') and self.audio_visualizer:
                self.audio_visualizer.stop_recording()

            # 停止更新定时器
            if hasattr(self, 'update_timer'):
                self.update_timer.stop()

            event.accept()

        except Exception as e:
            logger.error(f"关闭应用时出错: {e}")
            event.accept()


def main():
    """主函数"""
    try:
        app = QApplication(sys.argv)
        app.setApplicationName("OpenAI实时语音转文字工具 Pro")
        app.setApplicationVersion("1.0")

        # 检查依赖
        missing_deps = []

        try:
            import websocket
        except ImportError:
            missing_deps.append("websocket-client")

        try:
            import openai
        except ImportError:
            missing_deps.append("openai")

        try:
            import pyaudio
        except ImportError:
            missing_deps.append("pyaudio")

        if missing_deps:
            print("❌ 缺少以下必需依赖包:")
            for dep in missing_deps:
                print(f"  pip install {dep}")
            print("\n📦 可选依赖包:")
            print("  pip install pyqtgraph  # 更好的音频可视化")
            print("  pip install pydub      # 大文件处理支持")
            sys.exit(1)

        if not HAS_PYQTGRAPH:
            print("💡 建议安装 pyqtgraph 以获得更好的音频可视化:")
            print("  pip install pyqtgraph")

        if not HAS_PYDUB:
            print("💡 建议安装 pydub 以支持大文件转录:")
            print("  pip install pydub")

        print("🚀 启动OpenAI实时语音转文字工具 Pro v1.0...")

        # 创建应用实例
        window = UltraRealtimeSubtitleApp()
        window.show()

        sys.exit(app.exec_())

    except Exception as e:
        logger.error(f"启动应用失败: {e}")
        print(f"❌ 启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
