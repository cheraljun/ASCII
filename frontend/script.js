// 全局变量
let currentFile = null;
let currentFileType = null; // 'image' or 'video'
let currentAsciiText = null;
let isConverting = false;
let conversionTimeout = null;

// 视频相关
let videoInfo = null;
let videoPath = null;
let isPlaying = false;
let playInterval = null;
let currentTime = 0;

// DOM元素（等待页面加载后初始化）
let uploadArea, fileInput, uploadText, fileTypeIndicator, resultContainer;
let widthInput, widthValue, contrastInput, contrastValue;
let colorRadios;
let videoControls, playPauseBtn, stopBtn, videoTimeline, currentTimeDisplay, totalTimeDisplay;
let exportProgress, progressFill, progressText;
let exportImageBtn, exportVideoBtn, exportGifBtn;

// ===== 初始化 =====

function initializeDOM() {
    // DOM元素
    uploadArea = document.getElementById('uploadArea');
    fileInput = document.getElementById('fileInput');
    uploadText = uploadArea.querySelector('.upload-text');
    fileTypeIndicator = document.getElementById('fileTypeIndicator');
    resultContainer = document.getElementById('resultContainer');

    // 参数元素
    widthInput = document.getElementById('width');
    widthValue = document.getElementById('widthValue');
    contrastInput = document.getElementById('contrast');
    contrastValue = document.getElementById('contrastValue');
    colorRadios = document.querySelectorAll('input[name="color"]');

    // 视频控制
    videoControls = document.getElementById('videoControls');
    playPauseBtn = document.getElementById('playPauseBtn');
    stopBtn = document.getElementById('stopBtn');
    videoTimeline = document.getElementById('videoTimeline');
    currentTimeDisplay = document.getElementById('currentTime');
    totalTimeDisplay = document.getElementById('totalTime');

    // 导出进度
    exportProgress = document.getElementById('exportProgress');
    progressFill = document.getElementById('progressFill');
    progressText = document.getElementById('progressText');

    // 下载按钮
    exportImageBtn = document.getElementById('exportImageBtn');
    exportVideoBtn = document.getElementById('exportVideoBtn');
    exportGifBtn = document.getElementById('exportGifBtn');
    
    // 初始化完成后设置事件监听
    setupEventListeners();
}

// ===== 工具函数 =====

function debounce(func, wait) {
    return function(...args) {
        clearTimeout(conversionTimeout);
        conversionTimeout = setTimeout(() => func.apply(this, args), wait);
    };
}

function showLoading() {
    resultContainer.innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
            <div>正在转换中...</div>
        </div>
    `;
}

function showResult(asciiText) {
    currentAsciiText = asciiText;
    const params = getParams();
    const colorClass = `color-${params.color}`;
    resultContainer.innerHTML = `<div class="result-preview ${colorClass}">${escapeHtml(asciiText)}</div>`;
}

function showError(message) {
    resultContainer.innerHTML = `
        <div class="loading">
            <div style="color: #dc3545; font-size: 2rem; margin-bottom: 10px;">❌</div>
            <div style="color: #dc3545;">错误: ${message}</div>
        </div>
    `;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function getParams() {
    // 获取选中的颜色
    let selectedColor = 'white';
    for (const radio of colorRadios) {
        if (radio.checked) {
            selectedColor = radio.value;
            break;
        }
    }
    
    return {
        width: parseInt(widthInput.value),
        contrast: parseFloat(contrastInput.value),
        color: selectedColor
    };
}

// ===== 图片转换 =====

async function convertImage() {
    if (!currentFile || currentFileType !== 'image' || isConverting) return;
    
    isConverting = true;
    showLoading();
    
    const formData = new FormData();
    formData.append('file', currentFile);
    
    const params = getParams();
    Object.keys(params).forEach(key => {
        formData.append(key, params[key]);
    });
    
    try {
        const response = await fetch('/api/convert/image', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            showResult(result.data.text);
        } else {
            showError(result.error);
        }
    } catch (error) {
        showError(error.message);
    } finally {
        isConverting = false;
    }
}

// ===== 视频处理 =====

async function loadVideo() {
    if (!currentFile || currentFileType !== 'video') return;
    
    showLoading();
    
    const formData = new FormData();
    formData.append('file', currentFile);
    
    try {
        const response = await fetch('/api/convert/video/info', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            videoInfo = result.data;
            videoPath = result.video_path;
            
            // 更新UI
            videoControls.classList.remove('hidden');
            exportVideoBtn.classList.remove('hidden');
            exportGifBtn.classList.remove('hidden');
            
            videoTimeline.max = videoInfo.duration;
            totalTimeDisplay.textContent = videoInfo.duration.toFixed(1) + 's';
            
            // 显示第一帧
            await showVideoFrame(0);
        } else {
            showError(result.error);
        }
    } catch (error) {
        showError(error.message);
    }
}

async function showVideoFrame(timeSec) {
    if (!videoPath || isConverting) return;
    
    isConverting = true;
    currentTime = timeSec;
    
    const formData = new FormData();
    formData.append('video_path', videoPath);
    formData.append('time_sec', timeSec);
    
    const params = getParams();
    Object.keys(params).forEach(key => {
        formData.append(key, params[key]);
    });
    
    try {
        const response = await fetch('/api/convert/video/frame', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            showResult(result.data.text);
            currentTimeDisplay.textContent = timeSec.toFixed(1) + 's';
            videoTimeline.value = timeSec;
        } else {
            showError(result.error);
        }
    } catch (error) {
        showError(error.message);
    } finally {
        isConverting = false;
    }
}

function playVideo() {
    if (!videoInfo || isPlaying) return;
    
    isPlaying = true;
    playPauseBtn.textContent = '暂停';
    
    const frameInterval = 1000 / videoInfo.fps; // 毫秒
    
    playInterval = setInterval(async () => {
        currentTime += (1 / videoInfo.fps);
        
        if (currentTime >= videoInfo.duration) {
            stopVideo();
            return;
        }
        
        await showVideoFrame(currentTime);
    }, frameInterval);
}

function pauseVideo() {
    if (!isPlaying) return;
    
    isPlaying = false;
    playPauseBtn.textContent = '播放';
    
    if (playInterval) {
        clearInterval(playInterval);
        playInterval = null;
    }
}

function stopVideo() {
    pauseVideo();
    currentTime = 0;
    showVideoFrame(0);
}

// 导出为图片
async function exportImage() {
    if (!currentFile) {
        alert('请先上传图片或视频');
        return;
    }
    
    const formData = new FormData();
    
    if (currentFileType === 'image') {
        formData.append('file', currentFile);
    } else if (currentFileType === 'video') {
        formData.append('video_path', videoPath);
        formData.append('time_sec', currentTime);
    }
    
    const params = getParams();
    Object.keys(params).forEach(key => {
        formData.append(key, params[key]);
    });
    
    try {
        const endpoint = currentFileType === 'image' 
            ? '/api/convert/image/export_png' 
            : '/api/convert/video/export_frame_png';
            
        const response = await fetch(endpoint, {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'ascii_art.png';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        } else {
            const result = await response.json();
            alert('导出失败: ' + (result.error || '未知错误'));
        }
    } catch (error) {
        alert('导出失败: ' + error.message);
    }
}

// 导出ASCII视频
async function exportAsciiVideo() {
    if (!videoPath) return;
    
    // 暂停视频播放
    if (isPlaying) {
        pauseVideo();
    }
    
    // 禁用播放控制
    playPauseBtn.disabled = true;
    stopBtn.disabled = true;
    videoTimeline.disabled = true;
    
    exportProgress.classList.remove('hidden');
    exportVideoBtn.disabled = true;
    exportVideoBtn.textContent = '正在导出...';
    
    // 模拟进度（基于帧数估算，视频渲染更慢）
    const estimatedTime = videoInfo.frame_count * 100; // 每帧约100ms
    simulateProgress(estimatedTime);
    
    const formData = new FormData();
    formData.append('video_path', videoPath);
    formData.append('filename', currentFile.name);
    
    const params = getParams();
    Object.keys(params).forEach(key => {
        formData.append(key, params[key]);
    });
    
    try {
        const response = await fetch('/api/convert/video/export_video', {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            // 清除定时器，立即跳到100%
            clearProgressTimer();
            progressFill.style.width = '100%';
            progressText.textContent = '100%';
            
            const blob = await response.blob();
            const fileName = currentFile.name.split('.')[0];
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${fileName}_ascii.mp4`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            
            setTimeout(() => {
                alert('ASCII视频导出成功！');
            }, 300);
        } else {
            clearProgressTimer();
            const result = await response.json();
            alert('导出失败: ' + (result.error || '未知错误'));
        }
    } catch (error) {
        clearProgressTimer();
        alert('导出失败: ' + error.message);
    } finally {
        exportVideoBtn.disabled = false;
        exportVideoBtn.textContent = '导出 ASCII 视频';
        
        // 恢复播放控制
        playPauseBtn.disabled = false;
        stopBtn.disabled = false;
        videoTimeline.disabled = false;
        
        setTimeout(() => {
            exportProgress.classList.add('hidden');
            progressFill.style.width = '0%';
            progressText.textContent = '0%';
        }, 1000);
    }
}

// 导出ASCII GIF
async function exportAsciiGif() {
    if (!videoPath) return;
    
    // 暂停视频播放
    if (isPlaying) {
        pauseVideo();
    }
    
    // 禁用播放控制
    playPauseBtn.disabled = true;
    stopBtn.disabled = true;
    videoTimeline.disabled = true;
    
    exportProgress.classList.remove('hidden');
    exportGifBtn.disabled = true;
    exportGifBtn.textContent = '正在导出...';
    
    // 模拟进度（GIF需要先导出视频，时间和视频导出相近）
    const estimatedTime = videoInfo.frame_count * 100; // 每帧约100ms
    simulateProgress(estimatedTime);
    
    const formData = new FormData();
    formData.append('video_path', videoPath);
    formData.append('filename', currentFile.name);
    
    const params = getParams();
    Object.keys(params).forEach(key => {
        formData.append(key, params[key]);
    });
    
    try {
        const response = await fetch('/api/convert/video/export_gif', {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            // 清除定时器，立即跳到100%
            clearProgressTimer();
            progressFill.style.width = '100%';
            progressText.textContent = '100%';
            
            const blob = await response.blob();
            const fileName = currentFile.name.split('.')[0];
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${fileName}_ascii.gif`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            
            setTimeout(() => {
                alert('ASCII GIF导出成功！');
            }, 300);
        } else {
            clearProgressTimer();
            const result = await response.json();
            alert('导出失败: ' + (result.error || '未知错误'));
        }
    } catch (error) {
        clearProgressTimer();
        alert('导出失败: ' + error.message);
    } finally {
        exportGifBtn.disabled = false;
        exportGifBtn.textContent = '导出 ASCII GIF';
        
        // 恢复播放控制
        playPauseBtn.disabled = false;
        stopBtn.disabled = false;
        videoTimeline.disabled = false;
        
        setTimeout(() => {
            exportProgress.classList.add('hidden');
            progressFill.style.width = '0%';
            progressText.textContent = '0%';
        }, 1000);
    }
}

// 模拟进度条动画
let progressInterval = null;
function simulateProgress(estimatedTime) {
    // 清除之前的进度
    if (progressInterval) {
        clearInterval(progressInterval);
    }
    
    let progress = 0;
    const totalSteps = 98; // 到98%，留2%给最终处理
    const interval = estimatedTime / totalSteps;
    
    progressInterval = setInterval(() => {
        if (progress < totalSteps) {
            progress += 1;
            progressFill.style.width = progress + '%';
            progressText.textContent = progress + '%';
        }
    }, interval);
}

// 清除进度定时器
function clearProgressTimer() {
    if (progressInterval) {
        clearInterval(progressInterval);
        progressInterval = null;
    }
}

// ===== 事件监听设置 =====

function setupEventListeners() {
    // 参数改变时实时转换（使用防抖）
    const debouncedConvert = debounce(() => {
        if (currentFileType === 'image') {
            convertImage();
        } else if (currentFileType === 'video' && !isPlaying) {
            showVideoFrame(currentTime);
        }
    }, 300);

    widthInput.addEventListener('input', (e) => {
        widthValue.textContent = e.target.value;
        debouncedConvert();
    });

    contrastInput.addEventListener('input', (e) => {
        contrastValue.textContent = e.target.value;
        debouncedConvert();
    });

    // 颜色改变时实时转换
    colorRadios.forEach(radio => {
        radio.addEventListener('change', () => {
            debouncedConvert();
        });
    });

    // 上传区域点击
    uploadArea.addEventListener('click', () => {
        fileInput.click();
    });

    // 文件选择
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileUpload(e.target.files[0]);
        }
    });

    // 拖拽上传
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        
        if (e.dataTransfer.files.length > 0) {
            handleFileUpload(e.dataTransfer.files[0]);
        }
    });

    // 视频控制按钮
    playPauseBtn.addEventListener('click', () => {
        if (isPlaying) {
            pauseVideo();
        } else {
            playVideo();
        }
    });

    stopBtn.addEventListener('click', () => {
        stopVideo();
    });

    videoTimeline.addEventListener('input', (e) => {
        if (isPlaying) {
            pauseVideo();
        }
        const time = parseFloat(e.target.value);
        showVideoFrame(time);
    });

    // 导出图片按钮
    exportImageBtn.addEventListener('click', exportImage);
    exportVideoBtn.addEventListener('click', exportAsciiVideo);
    exportGifBtn.addEventListener('click', exportAsciiGif);
}

// 处理文件上传
function handleFileUpload(file) {
    // 停止当前播放
    if (isPlaying) {
        pauseVideo();
    }
    
    currentFile = file;
    uploadText.textContent = `已选择: ${file.name}`;
    
    // 判断文件类型
    const fileType = file.type;
    if (fileType.startsWith('image/')) {
        currentFileType = 'image';
        fileTypeIndicator.textContent = '图片模式';
        fileTypeIndicator.className = 'file-type-indicator image';
        
        videoControls.classList.add('hidden');
        exportVideoBtn.classList.add('hidden');
        exportGifBtn.classList.add('hidden');
        
        // 立即转换图片
        convertImage();
    } else if (fileType.startsWith('video/')) {
        currentFileType = 'video';
        fileTypeIndicator.textContent = '视频模式';
        fileTypeIndicator.className = 'file-type-indicator video';
        
        // 加载视频
        loadVideo();
    } else {
        showError('不支持的文件类型');
    }
}

// ===== 页面加载完成后初始化 =====
document.addEventListener('DOMContentLoaded', initializeDOM);
