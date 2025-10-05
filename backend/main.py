from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import shutil
import zipfile
from pathlib import Path
from ascii_maker import ImageToASCII, VideoToASCII
import tempfile
import time
import random
import string

app = FastAPI(title="Image to ASCII Converter")

# CORS设置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 创建上传目录
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# 挂载前端静态文件
app.mount("/static", StaticFiles(directory="frontend"), name="static")

def generate_safe_filename(prefix: str = "file") -> str:
    """生成安全的文件名：前缀_时间戳_随机字符"""
    timestamp = int(time.time())
    random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"{prefix}_{timestamp}_{random_str}"

@app.get("/")
async def root():
    """返回前端页面"""
    return FileResponse("frontend/index.html")

@app.post("/api/convert/image")
async def convert_image(
    file: UploadFile = File(...),
    width: int = Form(100),
    contrast: float = Form(1.0),
    color: str = Form('white')
):
    """
    图片转ASCII接口
    """
    try:
        # 保存上传的文件
        file_path = UPLOAD_DIR / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 创建转换器
        converter = ImageToASCII(
            width=width,
            contrast=contrast,
            color=color
        )
        
        # 执行转换
        ascii_text = converter.convert_to_ascii(str(file_path))
        
        # 删除临时文件
        os.remove(file_path)
        
        return JSONResponse(content={
            "success": True,
            "data": {
                "text": ascii_text
            }
        })
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )

@app.post("/api/convert/video/info")
async def get_video_info(file: UploadFile = File(...)):
    """
    获取视频信息
    """
    try:
        # 保存上传的文件
        file_path = UPLOAD_DIR / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 获取视频信息
        converter = VideoToASCII()
        info = converter.get_video_info(str(file_path))
        
        return JSONResponse(content={
            "success": True,
            "data": info,
            "video_path": str(file_path)
        })
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )

@app.post("/api/convert/video/frame")
async def convert_video_frame(
    video_path: str = Form(...),
    time_sec: float = Form(0),
    width: int = Form(100),
    contrast: float = Form(1.0),
    color: str = Form('white')
):
    """
    转换视频指定时间点的帧
    """
    try:
        # 创建转换器
        converter = VideoToASCII(
            width=width,
            contrast=contrast,
            color=color
        )
        
        # 获取指定帧
        ascii_frame = converter.get_frame_at_time(video_path, time_sec)
        
        return JSONResponse(content={
            "success": True,
            "data": {
                "text": ascii_frame
            }
        })
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )

@app.post("/api/convert/video/export_frames")
async def export_video_frames(
    video_path: str = Form(...),
    filename: str = Form(...),
    width: int = Form(100),
    contrast: float = Form(1.0),
    color: str = Form('white')
):
    """
    导出视频所有帧为TXT文件（打包成ZIP，以文件名命名）
    """
    try:
        # 生成安全的文件名
        safe_base_name = generate_safe_filename("ascii_frames")

        # 限制最大安全宽度
        safe_width = min(width, 150)
        
        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / safe_base_name
            
            # 创建转换器
            converter = VideoToASCII(
                width=safe_width,
                contrast=contrast,
                color=color
            )
            
            # 提取所有帧
            frame_files = converter.extract_all_frames(video_path, str(output_dir))
            
            # 打包成ZIP - 使用安全的文件名
            safe_zip_name = f"{safe_base_name}.zip"
            zip_path = Path(temp_dir) / safe_zip_name
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for frame_file in frame_files:
                    # 保持文件夹结构
                    arcname = os.path.join(safe_base_name, os.path.basename(frame_file))
                    zipf.write(frame_file, arcname)
            
            # 读取ZIP文件内容
            with open(zip_path, 'rb') as f:
                zip_content = f.read()
        
            # 返回ZIP文件
        return StreamingResponse(
            iter([zip_content]),
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={safe_zip_name}"
            }
        )
    
    except Exception as e:
        import traceback
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"{str(e)}\n{traceback.format_exc()}"
            }
        )

@app.post("/api/convert/video/export_video")
async def export_ascii_video(
    video_path: str = Form(...),
    filename: str = Form(...),
    width: int = Form(100),
    contrast: float = Form(1.0),
    color: str = Form('white')
):
    """
    导出ASCII视频文件
    """
    try:
        # 限制宽度以保证稳定性
        safe_width = min(width, 150)
        
        # 生成安全的文件名
        safe_filename = generate_safe_filename("ascii_video") + ".mp4"
        
        # 创建转换器
        converter = VideoToASCII(
            width=safe_width,
            contrast=contrast,
            color=color
        )
        
        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            # 使用安全的文件名
            output_video = Path(temp_dir) / safe_filename
            
            # 生成ASCII视频
            converter.export_video(video_path, str(output_video))
            
            # 读取视频文件
            with open(output_video, 'rb') as f:
                video_content = f.read()
        
        # 不删除原视频文件，保持页面状态
        
        # 返回视频文件
        return StreamingResponse(
            iter([video_content]),
            media_type="video/mp4",
            headers={
                "Content-Disposition": f"attachment; filename={safe_filename}"
            }
        )
    
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"{str(e)}\n{error_detail}"
            }
        )

@app.post("/api/convert/video/export_gif")
async def export_ascii_gif(
    video_path: str = Form(...),
    filename: str = Form(...),
    width: int = Form(100),
    contrast: float = Form(1.0),
    color: str = Form('white')
):
    """
    导出ASCII GIF文件（不跳帧）
    """
    try:
        # 限制宽度以保证稳定性（和视频导出一致）
        safe_width = min(width, 150)
        
        # 生成安全的文件名
        safe_filename = generate_safe_filename("ascii_gif") + ".gif"
        
        # 创建转换器
        converter = VideoToASCII(
            width=safe_width,
            contrast=contrast,
            color=color
        )
        
        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            # 使用安全的文件名
            output_gif = Path(temp_dir) / safe_filename
            
            # 生成ASCII GIF（不跳帧）
            converter.export_gif(video_path, str(output_gif))
            
            # 读取GIF文件
            with open(output_gif, 'rb') as f:
                gif_content = f.read()
        
        # 返回GIF文件
        return StreamingResponse(
            iter([gif_content]),
            media_type="image/gif",
            headers={
                "Content-Disposition": f"attachment; filename={safe_filename}"
            }
        )
    
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"{str(e)}\n{error_detail}"
            }
        )

@app.post("/api/convert/image/export_png")
async def export_image_png(
    file: UploadFile = File(...),
    width: int = Form(100),
    contrast: float = Form(1.0),
    color: str = Form('white')
):
    """
    导出图片为PNG
    """
    try:
        # 保存上传的文件
        file_path = UPLOAD_DIR / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 创建转换器
        converter = ImageToASCII(
            width=width,
            contrast=contrast,
            color=color
        )
        
        # 生成安全的文件名
        safe_filename = generate_safe_filename("ascii_image") + ".png"
        
        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            output_png = Path(temp_dir) / safe_filename
            
            # 导出为PNG
            converter.export_image_to_png(str(file_path), str(output_png))
            
            # 读取PNG文件
            with open(output_png, 'rb') as f:
                png_content = f.read()
        
        # 删除上传的临时文件
        os.remove(file_path)
        
        # 返回PNG文件
        return StreamingResponse(
            iter([png_content]),
            media_type="image/png",
            headers={
                "Content-Disposition": f"attachment; filename={safe_filename}"
            }
        )
    
    except Exception as e:
        import traceback
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"{str(e)}\n{traceback.format_exc()}"
            }
        )

@app.post("/api/convert/video/export_frame_png")
async def export_video_frame_png(
    video_path: str = Form(...),
    time_sec: float = Form(0),
    width: int = Form(100),
    contrast: float = Form(1.0),
    color: str = Form('white')
):
    """
    导出视频帧为PNG
    """
    try:
        # 限制宽度
        safe_width = min(width, 150)
        
        # 创建转换器
        converter = VideoToASCII(
            width=safe_width,
            contrast=contrast,
            color=color
        )
        
        # 生成安全的文件名
        safe_filename = generate_safe_filename("ascii_frame") + ".png"
        
        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            output_png = Path(temp_dir) / safe_filename
            
            # 导出为PNG
            converter.export_frame_to_png(video_path, time_sec, str(output_png))
            
            # 读取PNG文件
            with open(output_png, 'rb') as f:
                png_content = f.read()
        
        # 返回PNG文件
        return StreamingResponse(
            iter([png_content]),
            media_type="image/png",
            headers={
                "Content-Disposition": f"attachment; filename={safe_filename}"
            }
        )
    
    except Exception as e:
        import traceback
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"{str(e)}\n{traceback.format_exc()}"
            }
        )

@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
