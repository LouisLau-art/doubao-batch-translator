
import zipfile
import re
import os
import shutil
import tempfile

def clean_epub(epub_path):
    print(f"🧹 正在清理: {os.path.basename(epub_path)}")
    
    fixed_count = 0
    backup_path = epub_path + ".backup"
    
    if not os.path.exists(backup_path):
        shutil.copy2(epub_path, backup_path)
        print(f"📦 已创建备份: {os.path.basename(backup_path)}")

    with tempfile.TemporaryDirectory() as temp_dir:
        # 解压
        with zipfile.ZipFile(epub_path, 'r') as zf:
            zf.extractall(temp_dir)
            
        # 遍历处理
        for root, _, files in os.walk(temp_dir):
            for fname in files:
                if fname.endswith(('.html', '.xhtml', '.htm')):
                    fpath = os.path.join(root, fname)
                    with open(fpath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 查找并移除 <!--?xml ... ?--> 模式
                    # 使用非贪婪匹配 .*?
                    new_content = re.sub(r'<!--\?xml.*?\?-->', '', content)
                    
                    if len(new_content) != len(content):
                        with open(fpath, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        fixed_count += 1
                        # print(f"   ✨ 修复: {fname}")

        # 重新打包
        with zipfile.ZipFile(epub_path, 'w', zipfile.ZIP_DEFLATED) as zf:
             # 先把 mimetype 写入 (必须是第一个文件且无压缩)
            mimetype_path = os.path.join(temp_dir, 'mimetype')
            if os.path.exists(mimetype_path):
                zf.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)

            for root, _, files in os.walk(temp_dir):
                for f in files:
                    full_path = os.path.join(root, f)
                    arc_name = os.path.relpath(full_path, temp_dir)
                    if arc_name == 'mimetype': continue
                    zf.write(full_path, arc_name)
    
    print(f"✅ 清理完成！修复了 {fixed_count} 个文件中的冗余 XML 声明。")

if __name__ == "__main__":
    target_file = "/home/louis/doubao-batch-translator/translated/Legends Lattes A Novel of High Fantasy and Low Stakes (Travis Baldree) (Z-Library)_translated.epub"
    if os.path.exists(target_file):
        clean_epub(target_file)
    else:
        print(f"❌ 文件未找到: {target_file}")
