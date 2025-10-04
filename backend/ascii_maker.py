from PIL import Image, ImageEnhance
import cv2
import numpy as np
from typing import Dict, List
import os

class ImageToASCII:
    """图片转ASCII核心转换器"""
    
    CHARS_SETS = {
        'simple': " .:-=+*#%@",
        'standard': " .'`^\",:;Il!i~+_-?]}{1)(|/tfjrxnuvcz*#MW&8%@",
        'detailed': " .'`^\",:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"
    }
    
    def __init__(self, 
                 width: int = 100,
                 chars_type: str = 'standard',
                 scale: float = 0.43,
                 invert: bool = False,
                 colored: bool = False,
                 brightness: int = 0,
                 contrast: float = 1.0):
        
        self.width = width
        self.chars = self.CHARS_SETS.get(chars_type, self.CHARS_SETS['standard'])
        self.scale = scale
        self.invert = invert
        self.colored = colored
        self.brightness = brightness
        self.contrast = contrast
        
        # 如果需要反转，反转字符集
        if self.invert:
            self.chars = self.chars[::-1]
    
    def resize_image(self, image: Image.Image) -> Image.Image:
        """调整图片尺寸，保持宽高比"""
        original_width, original_height = image.size
        aspect_ratio = original_height / original_width
        new_height = int(self.width * aspect_ratio * self.scale)
        return image.resize((self.width, new_height))
    
    def adjust_image(self, image: Image.Image) -> Image.Image:
        """调整亮度和对比度"""
        # 调整对比度
        if self.contrast != 1.0:
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(self.contrast)
        
        # 调整亮度
        if self.brightness != 0:
            enhancer = ImageEnhance.Brightness(image)
            brightness_factor = 1.0 + (self.brightness / 100)
            image = enhancer.enhance(brightness_factor)
        
        return image
    
    def get_char(self, brightness: int) -> str:
        """根据亮度值获取对应的ASCII字符"""
        char_index = int((brightness / 255) * (len(self.chars) - 1))
        return self.chars[char_index]
    
    def rgb_to_ansi(self, r: int, g: int, b: int) -> str:
        """将RGB颜色转换为ANSI转义码"""
        return f"\033[38;2;{r};{g};{b}m"
    
    def convert_to_ascii(self, image_path: str) -> str:
        """转换为ASCII文本"""
        # 打开图片
        image = Image.open(image_path)
        
        # 调整尺寸
        image = self.resize_image(image)
        
        # 调整亮度和对比度
        image = self.adjust_image(image)
        
        # 根据是否彩色选择处理方式
        if self.colored:
            rgb_image = image.convert('RGB')
            grayscale_image = image.convert('L')
        else:
            grayscale_image = image.convert('L')
            rgb_image = None
        
        # 转换为ASCII
        ascii_str = ""
        for y in range(grayscale_image.height):
            for x in range(grayscale_image.width):
                brightness = grayscale_image.getpixel((x, y))
                char = self.get_char(brightness)
                
                if self.colored and rgb_image:
                    r, g, b = rgb_image.getpixel((x, y))
                    ascii_str += self.rgb_to_ansi(r, g, b) + char
                else:
                    ascii_str += char
            
            # 重置颜色并换行
            if self.colored:
                ascii_str += "\033[0m"
            ascii_str += '\n'
        
        # 最后重置颜色
        if self.colored:
            ascii_str += "\033[0m"
        
        return ascii_str


class VideoToASCII:
    """视频转ASCII转换器"""
    
    def __init__(self, 
                 width: int = 100,
                 chars_type: str = 'standard',
                 scale: float = 0.43,
                 invert: bool = False,
                 colored: bool = False,
                 brightness: int = 0,
                 contrast: float = 1.0):
        
        self.converter = ImageToASCII(
            width=width,
            chars_type=chars_type,
            scale=scale,
            invert=invert,
            colored=colored,
            brightness=brightness,
            contrast=contrast
        )
    
    def get_video_info(self, video_path: str) -> Dict:
        """获取视频信息"""
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps if fps > 0 else 0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        
        return {
            'fps': fps,
            'frame_count': frame_count,
            'duration': duration,
            'width': width,
            'height': height
        }
    
    def convert_frame(self, frame: np.ndarray) -> str:
        """转换单帧为ASCII"""
        # 将OpenCV的BGR转为RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # 转为PIL Image
        image = Image.fromarray(frame_rgb)
        
        # 调整尺寸
        image = self.converter.resize_image(image)
        
        # 调整亮度和对比度
        image = self.converter.adjust_image(image)
        
        # 转换为ASCII
        if self.converter.colored:
            rgb_image = image.convert('RGB')
            grayscale_image = image.convert('L')
        else:
            grayscale_image = image.convert('L')
            rgb_image = None
        
        ascii_str = ""
        for y in range(grayscale_image.height):
            for x in range(grayscale_image.width):
                brightness = grayscale_image.getpixel((x, y))
                char = self.converter.get_char(brightness)
                
                if self.converter.colored and rgb_image:
                    r, g, b = rgb_image.getpixel((x, y))
                    ascii_str += self.converter.rgb_to_ansi(r, g, b) + char
                else:
                    ascii_str += char
            
            if self.converter.colored:
                ascii_str += "\033[0m"
            ascii_str += '\n'
        
        if self.converter.colored:
            ascii_str += "\033[0m"
        
        return ascii_str
    
    def extract_all_frames(self, video_path: str, output_dir: str) -> List[str]:
        """提取视频所有帧并转换为ASCII，保存到文件"""
        cap = cv2.VideoCapture(video_path)
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        frame_files = []
        frame_index = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # 转换帧
            ascii_frame = self.convert_frame(frame)
            
            # 保存到文件
            frame_file = os.path.join(output_dir, f'frame_{frame_index:06d}.txt')
            with open(frame_file, 'w', encoding='utf-8') as f:
                f.write(ascii_frame)
            
            frame_files.append(frame_file)
            frame_index += 1
        
        cap.release()
        return frame_files
    
    def get_frame_at_time(self, video_path: str, time_sec: float) -> str:
        """获取指定时间点的帧并转换为ASCII"""
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        # 定位到指定帧
        frame_number = int(time_sec * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            return ""
        
        return self.convert_frame(frame)
    
    def export_video(self, video_path: str, output_path: str):
        """将视频转换为ASCII视频文件"""
        # 限制宽度以避免编码问题
        safe_width = min(self.converter.width, 150)
        original_width = self.converter.width
        self.converter.width = safe_width
        
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        # 读取第一帧来确定ASCII尺寸
        ret, first_frame = cap.read()
        if not ret:
            cap.release()
            self.converter.width = original_width
            raise Exception("无法读取视频帧")
        
        ascii_first = self.convert_frame(first_frame)
        # 清理ANSI转义码和非ASCII字符
        ascii_first = self._sanitize_ascii(ascii_first)
        lines = ascii_first.strip().split('\n')
        ascii_height = len(lines)
        ascii_width = max(len(line) for line in lines) if lines else 0
        
        # 每个字符的像素尺寸
        char_width = 8
        char_height = 14
        
        frame_width = ascii_width * char_width
        frame_height = ascii_height * char_height
        
        # 确保输出路径是ASCII兼容的
        try:
            output_path.encode('ascii')
        except UnicodeEncodeError:
            # 如果路径包含非ASCII字符，使用临时文件名
            import tempfile
            output_path = tempfile.mktemp(suffix='.mp4')
        
        # 创建视频写入器
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))
        
        if not out.isOpened():
            cap.release()
            self.converter.width = original_width
            raise Exception("无法创建视频写入器")
        
        # 重置到开头
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        
        frame_count = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # 转换为ASCII
            ascii_frame = self.convert_frame(frame)
            # 清理为纯ASCII
            ascii_frame = self._sanitize_ascii(ascii_frame)
            
            # 将ASCII渲染为图像
            img = np.zeros((frame_height, frame_width, 3), dtype=np.uint8)
            
            lines = ascii_frame.strip().split('\n')
            for y, line in enumerate(lines):
                if y >= ascii_height:
                    break
                # 确保行宽度一致
                line = line.ljust(ascii_width)[:ascii_width]
                for x, char in enumerate(line):
                    if x >= ascii_width:
                        break
                    try:
                        cv2.putText(
                            img, 
                            char, 
                            (x * char_width, (y + 1) * char_height - 4), 
                            cv2.FONT_HERSHEY_PLAIN, 
                            1.0, 
                            (255, 255, 255), 
                            1
                        )
                    except Exception:
                        pass
            
            out.write(img)
            frame_count += 1
        
        cap.release()
        out.release()
        
        # 恢复原始宽度
        self.converter.width = original_width
    
    def _sanitize_ascii(self, text: str) -> str:
        """清理文本，只保留ASCII字符"""
        # 先移除ANSI转义码
        text = self._remove_ansi_codes(text)
        # 只保留ASCII字符（32-126）和换行符
        result = []
        for char in text:
            if char == '\n':
                result.append(char)
            elif 32 <= ord(char) <= 126:
                result.append(char)
            else:
                result.append(' ')
        return ''.join(result)
    
    def _remove_ansi_codes(self, text: str) -> str:
        """移除ANSI转义码"""
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)

