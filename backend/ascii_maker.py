from PIL import Image, ImageEnhance, ImageDraw, ImageFont
import cv2
import numpy as np
from typing import Dict, List
import os

class ImageToASCII:
    """图片转ASCII核心转换器"""
    
    # 字符集：从亮到暗的渐变
    CHARS = " .:-=#"
    
    # 颜色映射
    COLORS = {
        'white': (255, 255, 255),   # 白色 - 现代终端
        'yellow': (255, 255, 0),    # 黄色 - DOS风格
        'green': (0, 255, 0),        # 绿色 - 经典终端
        'orange': (255, 165, 0),    # 橙色 - 柔和暖色
        'cyan': (0, 255, 255)        # 青色 - 高对比度
    }
    
    def __init__(self, 
                 width: int = 100,
                 contrast: float = 1.0,
                 color: str = 'white'):
        
        self.width = width
        self.chars = self.CHARS
        self.scale = 0.43  # 固定宽高比
        self.contrast = contrast
        self.color = color
        self.color_rgb = self.COLORS.get(color, self.COLORS['white'])
    
    def resize_image(self, image: Image.Image) -> Image.Image:
        """调整图片尺寸，保持宽高比"""
        original_width, original_height = image.size
        aspect_ratio = original_height / original_width
        new_height = int(self.width * aspect_ratio * self.scale)
        return image.resize((self.width, new_height))
    
    def adjust_image(self, image: Image.Image) -> Image.Image:
        """调整对比度"""
        if self.contrast != 1.0:
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(self.contrast)
        return image
    
    def get_char(self, brightness: int) -> str:
        """根据亮度值获取对应的ASCII字符"""
        char_index = int((brightness / 255) * (len(self.chars) - 1))
        return self.chars[char_index]
    
    def convert_to_ascii(self, image_path: str) -> str:
        """转换为ASCII文本"""
        # 打开图片
        image = Image.open(image_path)
        
        # 调整尺寸
        image = self.resize_image(image)
        
        # 调整对比度
        image = self.adjust_image(image)
        
        # 转换为灰度图
        grayscale_image = image.convert('L')
        
        # 转换为ASCII
        ascii_str = ""
        for y in range(grayscale_image.height):
            for x in range(grayscale_image.width):
                brightness = grayscale_image.getpixel((x, y))
                char = self.get_char(brightness)
                ascii_str += char
            ascii_str += '\n'
        
        return ascii_str
    
    def export_image_to_png(self, image_path: str, output_path: str):
        """将图片转换为ASCII PNG"""
        # 打开并处理图片
        image = Image.open(image_path)
        image = self.resize_image(image)
        image = self.adjust_image(image)
        grayscale_image = image.convert('L')
        
        # 计算ASCII尺寸
        ascii_lines = []
        for y in range(grayscale_image.height):
            line = ""
            for x in range(grayscale_image.width):
                brightness = grayscale_image.getpixel((x, y))
                char = self.get_char(brightness)
                line += char
            ascii_lines.append(line)
        
        ascii_height = len(ascii_lines)
        ascii_width = max(len(line) for line in ascii_lines) if ascii_lines else 0
        
        # 字符像素尺寸
        char_width = 8
        char_height = 14
        
        frame_width = ascii_width * char_width
        frame_height = ascii_height * char_height
        
        # 创建图像
        img = np.zeros((frame_height, frame_width, 3), dtype=np.uint8)
        
        # 渲染ASCII
        for y, line in enumerate(ascii_lines):
            line = line.ljust(ascii_width)[:ascii_width]
            for x, char in enumerate(line):
                if x >= ascii_width:
                    break
                try:
                    color_bgr = (self.color_rgb[2], self.color_rgb[1], self.color_rgb[0])
                    cv2.putText(
                        img, 
                        char, 
                        (x * char_width, (y + 1) * char_height - 4), 
                        cv2.FONT_HERSHEY_PLAIN, 
                        1.0, 
                        color_bgr, 
                        1
                    )
                except Exception:
                    pass
        
        # 保存为PNG
        cv2.imwrite(output_path, img)


class VideoToASCII:
    """视频转ASCII转换器"""
    
    def __init__(self, 
                 width: int = 100,
                 contrast: float = 1.0,
                 color: str = 'white'):
        
        self.converter = ImageToASCII(
            width=width,
            contrast=contrast,
            color=color
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
        
        # 调整对比度
        image = self.converter.adjust_image(image)
        
        # 转换为灰度图
        grayscale_image = image.convert('L')
        
        # 转换为ASCII
        ascii_str = ""
        for y in range(grayscale_image.height):
            for x in range(grayscale_image.width):
                brightness = grayscale_image.getpixel((x, y))
                char = self.converter.get_char(brightness)
                ascii_str += char
            ascii_str += '\n'
        
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
    
    def export_frame_to_png(self, video_path: str, time_sec: float, output_path: str):
        """导出视频指定帧为PNG图片"""
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        # 定位到指定帧
        frame_number = int(time_sec * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            raise Exception("无法读取视频帧")
        
        # 转换为ASCII
        ascii_frame = self.convert_frame(frame)
        ascii_frame = self._sanitize_ascii(ascii_frame)
        
        lines = ascii_frame.strip().split('\n')
        ascii_height = len(lines)
        ascii_width = max(len(line) for line in lines) if lines else 0
        
        # 字符像素尺寸
        char_width = 8
        char_height = 14
        
        frame_width = ascii_width * char_width
        frame_height = ascii_height * char_height
        
        # 创建图像
        img = np.zeros((frame_height, frame_width, 3), dtype=np.uint8)
        
        # 渲染ASCII
        for y, line in enumerate(lines):
            line = line.ljust(ascii_width)[:ascii_width]
            for x, char in enumerate(line):
                if x >= ascii_width:
                    break
                try:
                    color_bgr = (self.converter.color_rgb[2], 
                                self.converter.color_rgb[1], 
                                self.converter.color_rgb[0])
                    cv2.putText(
                        img, 
                        char, 
                        (x * char_width, (y + 1) * char_height - 4), 
                        cv2.FONT_HERSHEY_PLAIN, 
                        1.0, 
                        color_bgr, 
                        1
                    )
                except Exception:
                    pass
        
        # 保存为PNG
        cv2.imwrite(output_path, img)
    
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
                        # 使用选定的颜色
                        color_bgr = (self.converter.color_rgb[2], 
                                    self.converter.color_rgb[1], 
                                    self.converter.color_rgb[0])  # RGB转BGR
                        cv2.putText(
                            img, 
                            char, 
                            (x * char_width, (y + 1) * char_height - 4), 
                            cv2.FONT_HERSHEY_PLAIN, 
                            1.0, 
                            color_bgr, 
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
    
    def export_gif(self, video_path: str, output_path: str):
        """将视频转换为 ASCII GIF（先转视频再转GIF，不跳帧）"""
        import tempfile
        from pathlib import Path
        
        # 步骤1: 先导出为 ASCII 视频（保存到磁盘）
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_video = Path(temp_dir) / "temp_ascii.mp4"
            
            # 调用现有方法导出视频（保持原帧率，不跳帧）
            self.export_video(video_path, str(temp_video))
            
            # 步骤2: 从磁盘读取生成的 ASCII 视频
            cap = cv2.VideoCapture(str(temp_video))
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            frames_list = []
            
            # 逐帧读取（不跳帧，保留所有帧）
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # OpenCV 读取的是 BGR，转为 RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                # 转为 PIL Image
                img = Image.fromarray(frame_rgb)
                frames_list.append(img)
            
            cap.release()
            
            # 步骤3: 保存为 GIF（保持原帧率）
            if frames_list:
                # 计算每帧持续时间（毫秒），保持原视频帧率
                duration = int(1000 / fps)
                frames_list[0].save(
                    output_path,
                    save_all=True,
                    append_images=frames_list[1:],
                    duration=duration,
                    loop=0,  # 无限循环
                    optimize=True  # 优化文件大小
                )

