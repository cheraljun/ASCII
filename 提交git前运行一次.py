import shutil
from pathlib import Path

for p in Path('.').rglob('*'):
    if p.is_dir() and p.name in ('uploads', '__pycache__'):
        shutil.rmtree(p)
        print(f'已删除: {p}')

print('清理完成！')
