import zipfile
import os

def create_test_epub(filename="mini_test.epub"):
    print(f"📚 正在生成测试文件: {filename} ...")
    
    with zipfile.ZipFile(filename, 'w') as zf:
        # 1. mimetype (必须是第一个，不压缩)
        zf.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        
        # 2. container.xml
        container_xml = """<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
    </rootfiles>
</container>"""
        zf.writestr("META-INF/container.xml", container_xml)
        
        # 3. content.opf (元数据)
        content_opf = """<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookId" version="2.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">
    <dc:title>The Little Prince (Test)</dc:title>
    <dc:creator>Test Author</dc:creator>
    <dc:description>This is a story about a little prince who travels across the universe.</dc:description>
    <dc:language>en</dc:language>
  </metadata>
  <manifest>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    <item id="ch1" href="chapter1.html" media-type="application/xhtml+xml"/>
    <item id="ch2" href="chapter2.html" media-type="application/xhtml+xml"/>
  </manifest>
  <spine toc="ncx">
    <itemref idref="ch1"/>
    <itemref idref="ch2"/>
  </spine>
</package>"""
        zf.writestr("OEBPS/content.opf", content_opf)
        
        # 4. toc.ncx (目录)
        toc_ncx = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN" "http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid" content="urn:uuid:12345"/>
  </head>
  <docTitle><text>The Little Prince (Test)</text></docTitle>
  <navMap>
    <navPoint id="navPoint-1" playOrder="1">
      <navLabel><text>Chapter 1: The Rose</text></navLabel>
      <content src="chapter1.html"/>
    </navPoint>
    <navPoint id="navPoint-2" playOrder="2">
      <navLabel><text>Chapter 2: The Fox</text></navLabel>
      <content src="chapter2.html"/>
    </navPoint>
  </navMap>
</ncx>"""
        zf.writestr("OEBPS/toc.ncx", toc_ncx)
        
        # 5. 正文内容
        chapter1_html = """<?xml version='1.0' encoding='utf-8'?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Chapter 1</title></head>
<body>
    <h1>Chapter 1: The Rose</h1>
    <p>Once when I was six years old I saw a magnificent picture in a book.</p>
    <p>It showed a boa constrictor swallowing an animal.</p>
    <div class="no-translate">This text should NOT be translated.</div>
</body>
</html>"""

        chapter2_html = """<?xml version='1.0' encoding='utf-8'?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Chapter 2</title></head>
<body>
    <h1>Chapter 2: The Fox</h1>
    <p>"To me, you are still nothing more than a little boy," said the fox.</p>
    <p>But if you tame me, then we shall need each other.</p>
    <code>print("Hello Code")</code>
</body>
</html>"""

        zf.writestr("OEBPS/chapter1.html", chapter1_html)
        zf.writestr("OEBPS/chapter2.html", chapter2_html)
        
    print(f"✅ 测试文件生成成功: {os.path.abspath(filename)}")

if __name__ == "__main__":
    create_test_epub()
