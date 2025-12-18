import streamlit as st
import io
import requests
import os
import traceback
from urllib.parse import urlparse

# --- 导入处理 ---
try:
    import docx
    from docx import Document
    from docx.shared import Pt, Cm, RGBColor
    from docx.oxml import parse_xml  
    from docx.oxml.ns import qn, nsmap 
    
    import mistletoe
    from mistletoe import block_token, span_token
    from mistletoe.base_renderer import BaseRenderer
    
    # 注册命名空间 (防止 KeyError: 'v')
    nsmap['v'] = 'urn:schemas-microsoft-com:vml'
    nsmap['o'] = 'urn:schemas-microsoft-com:office:office'
    
except ImportError as e:
    st.error(f"🚨 依赖库导入失败: {e}")
    st.stop()

# ==========================================
# 工具函数
# ==========================================
def get_available_font():
    """获取系统可用的中文字体（兼容跨平台）"""
    try:
        import win32api
        fonts = [font for font in win32api.GetFontFamilyNames() if '微软雅黑' in font]
        return fonts[0] if fonts else '宋体'
    except:
        # 非Windows系统 fallback
        return 'SimHei' if os.name == 'posix' else '宋体'

def setup_page_layout(doc, image_stream=None):
    """
    统一设置页面布局：A4尺寸、精确边距、背景图
    """
    # 1. 准备背景图关联 (如果有)
    bg_rId = None
    if image_stream:
        try:
            image_stream.seek(0)
            # 图片大小校验
            if image_stream.getbuffer().nbytes > 10 * 1024 * 1024:  # 10MB
                st.warning("⚠️ 背景图超过10MB，文档体积可能过大")
            bg_rId, _ = doc.part.get_or_add_image(image_stream)
        except Exception as e:
            st.error(f"背景图处理失败: {e}")

    # 2. 遍历所有章节进行设置
    for section in doc.sections:
        # --- A. 设置 A4 尺寸 ---
        section.page_width = Cm(21.0)
        section.page_height = Cm(29.7)
        
        # --- B. 设置精确边距 ---
        section.top_margin = Pt(72)
        section.bottom_margin = Pt(72)
        section.left_margin = Pt(54)
        section.right_margin = Pt(54)

        # --- C. 设置背景图 (VML) ---
        if bg_rId:
            section_element = section._sectPr
            
            # 构造 VML XML（优化格式）
            vmldata = (
                '<v:background id="_x0000_s1025" o:bwmode="white" fillcolor="white [3212]" '
                'xmlns:v="urn:schemas-microsoft-com:vml" '
                'xmlns:o="urn:schemas-microsoft-com:office:office">'
                f'<v:fill r:id="{bg_rId}" type="frame"/>'
                '</v:background>'
            )
            
            # 清除旧背景
            existing_bg = section_element.find(qn('v:background'))
            if existing_bg is not None:
                section_element.remove(existing_bg)
            
            # 插入新背景
            try:
                bg_element = parse_xml(vmldata)
                section_element.insert(0, bg_element)
            except Exception as e:
                st.warning(f"背景图XML解析失败: {e}")

# ==========================================
# Markdown 渲染器（兼容所有 mistletoe 版本）
# ==========================================
class DocxRenderer(BaseRenderer):
    def __init__(self, doc):
        self.doc = doc
        self.font_name = get_available_font()  # 动态获取字体
        
        # 设置默认样式
        style = doc.styles['Normal']
        font = style.font
        font.name = self.font_name
        font.size = Pt(10.5)
        font._element.rPr.rFonts.set(qn('w:eastAsia'), self.font_name)
        super().__init__()

    def render_document(self, token):
        if hasattr(token, 'children') and token.children:
            for child in token.children:
                self.render(child)

    def render_heading(self, token):
        level = token.level
        text = self.render_inner(token)
        p = self.doc.add_heading(text, level=level)
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(6)
        # 设置标题字体
        for run in p.runs:
            run.font.name = self.font_name
            run._element.rPr.rFonts.set(qn('w:eastAsia'), self.font_name)

    def render_paragraph(self, token):
        paragraph = self.doc.add_paragraph()
        self.render_inner(token, paragraph)

    def render_raw_text(self, token, parent_paragraph=None):
        content = token.content
        if parent_paragraph:
            run = parent_paragraph.add_run(content)
            run.font.name = self.font_name
            run._element.rPr.rFonts.set(qn('w:eastAsia'), self.font_name)
            return run
        return content

    def render_strong(self, token, parent_paragraph):
        run = self.render_inner(token, parent_paragraph)
        if run: 
            run.bold = True

    def render_emphasis(self, token, parent_paragraph):
        run = self.render_inner(token, parent_paragraph)
        if run: 
            run.italic = True
        
    def render_list(self, token):
        """
        兼容所有 mistletoe 版本的列表渲染
        - 旧版本：List 类 + start 属性
        - 新版本：OrderedList/UnorderedList 类
        """
        # 判定是否为有序列表（终极兼容方案）
        is_ordered = False
        
        # 适配新版本 mistletoe（有 OrderedList 类）
        if hasattr(block_token, 'OrderedList'):
            is_ordered = isinstance(token, block_token.OrderedList)
        # 适配旧版本 mistletoe（只有 List 类，通过 start 属性判断）
        else:
            is_ordered = hasattr(token, 'start') and token.start is not None
        
        # 设置列表样式（有序=数字，无序=圆点）
        list_style = 'List Number' if is_ordered else 'List Bullet'
        
        # 渲染列表项
        if hasattr(token, 'children') and token.children:
            for list_item in token.children:
                if hasattr(list_item, 'children') and list_item.children:
                    paragraph = self.doc.add_paragraph(style=list_style)
                    # 递归渲染列表项内容（支持嵌套）
                    self.render_list_item(list_item, paragraph)

    def render_list_item(self, token, parent_paragraph=None):
        """处理列表项（兼容所有版本，支持嵌套）"""
        if not parent_paragraph:
            parent_paragraph = self.doc.add_paragraph()
        
        for child in token.children:
            # 兼容所有版本的列表类判断
            list_classes = [block_token.List]
            if hasattr(block_token, 'OrderedList'):
                list_classes.append(block_token.OrderedList)
            if hasattr(block_token, 'UnorderedList'):
                list_classes.append(block_token.UnorderedList)
            
            if isinstance(child, tuple(list_classes)):
                self.render_list(child)  # 递归渲染嵌套列表
            else:
                self.render_inner(child, parent_paragraph)

    def render_image(self, token, parent_paragraph):
        url = token.src.strip()
        alt_text = token.title if token.title else "图片"
        image_stream = None

        try:
            if not url:
                raise ValueError("图片URL为空")
            
            # 区分网络/本地图片
            parsed = urlparse(url)
            if parsed.scheme in ('http', 'https'):
                response = requests.get(url, timeout=10, stream=True)
                response.raise_for_status()
                image_stream = io.BytesIO(response.content)
                response.close()
            elif os.path.exists(url):
                with open(url, 'rb') as f:
                    image_stream = io.BytesIO(f.read())
            else:
                raise FileNotFoundError(f"图片路径无效: {url}")

            # 插入图片（限制宽度）
            run = parent_paragraph.add_run()
            max_width = Cm(min(14, self.doc.sections[0].page_width.cm - 4))
            run.add_picture(image_stream, width=max_width)
            # 图片说明
            caption = parent_paragraph.add_run(f"\n{alt_text}")
            caption.italic = True
            caption.font.name = self.font_name

        except Exception as e:
            err_run = parent_paragraph.add_run(f"[图片加载失败: {alt_text} - {str(e)}]")
            err_run.font.color.rgb = RGBColor(255, 0, 0)
        finally:
            if image_stream:
                image_stream.close()

    def render_table(self, token):
        if not hasattr(token, 'children') or not token.children: 
            return
        rows = len(token.children)
        if rows == 0: 
            return
        
        first_row = token.children[0]
        if not hasattr(first_row, 'children') or not first_row.children: 
            return
        cols = len(first_row.children)
        
        table = self.doc.add_table(rows=rows, cols=cols)
        table.style = 'Table Grid' 

        for i, row_token in enumerate(token.children):
            row = table.rows[i]
            if hasattr(row_token, 'children') and row_token.children:
                for j, cell_token in enumerate(row_token.children):
                    if j < len(row.cells):
                        cell = row.cells[j]
                        cell._element.clear_content()
                        paragraph = cell.add_paragraph()
                        self.render_inner(cell_token, paragraph)
                        # 设置表格字体
                        for run in paragraph.runs:
                            run.font.name = self.font_name
                            run._element.rPr.rFonts.set(qn('w:eastAsia'), self.font_name)

    def render_inner(self, token, parent_paragraph=None):
        if hasattr(token, 'children') and token.children:
            last_run = None
            for child in token.children:
                if isinstance(child, span_token.RawText):
                    last_run = self.render_raw_text(child, parent_paragraph)
                elif isinstance(child, span_token.Strong):
                    self.render_strong(child, parent_paragraph)
                elif isinstance(child, span_token.Emphasis):
                    self.render_emphasis(child, parent_paragraph)
                elif isinstance(child, span_token.Image):
                    self.render_image(child, parent_paragraph)
            return last_run
        elif hasattr(token, 'content'):
            return self.render_raw_text(token, parent_paragraph)
        return None

# ==========================================
# 界面逻辑
# ==========================================
st.set_page_config(page_title="Huamai 文档生成器", layout="wide", page_icon="📄")
st.title("📄 Huamai 文档生成工具 (V5.2 最终修正)")

col1, col2 = st.columns([4, 6])

with col1:
    st.info("💡 请上传 A4 背景图（建议大小≤10MB）")
    bg_file = st.file_uploader("上传背景图 (PNG/JPG)", type=['png', 'jpg', 'jpeg'])
    generate_btn = st.button("🚀 生成文档", type="primary", use_container_width=True)

with col2:
    default_md = """# 产品规格说明书

## 1. 简介
本产品完全符合 A4 打印标准，页边距已严格校准。

## 2. 详细参数
| 项目 | 规格 | 说明 |
| :--- | :--- | :--- |
| 尺寸 | A4 | 标准纸张 |
| 边距 | 定制 | 72/72/54/54 pt |

## 3. 功能列表
- 支持Markdown语法
  - 标题、段落
  - 粗体、斜体
  - 有序/无序列表
- 图片插入（网络/本地）
- 表格渲染
- 自定义背景图

## 4. 有序列表示例
1. 第一步：输入Markdown内容
2. 第二步：上传背景图（可选）
3. 第三步：点击生成文档

## 5. 示例图片
![示例图片](https://picsum.photos/800/600)
"""
    md_input = st.text_area("Markdown 内容", height=500, value=default_md)

if generate_btn:
    if not md_input.strip():
        st.error("❌ 请输入 Markdown 内容！")
    else:
        with st.spinner("正在排版文档..."):
            try:
                # 初始化文档
                doc = Document()
                
                # 渲染Markdown内容
                renderer = DocxRenderer(doc)
                doc_token = mistletoe.Document(md_input)
                renderer.render(doc_token)
                
                # 处理背景图
                bg_stream = None
                if bg_file:
                    bg_stream = io.BytesIO(bg_file.getvalue())
                setup_page_layout(doc, bg_stream)
                
                # 保存文档到IO流
                doc_io = io.BytesIO()
                doc.save(doc_io)
                doc_io.seek(0)
                
                # 关闭临时流
                if bg_stream:
                    bg_stream.close()
                
                st.success("✅ 文档生成成功！")
                st.download_button(
                    label="📥 下载最终文档",
                    data=doc_io,
                    file_name="Huamai_Final_Fixed.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    type="primary",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"❌ 生成失败: {e}")
                st.expander("查看详细错误信息").code(traceback.format_exc())
