import streamlit as st
import docx
from docx import Document
from docx.shared import Pt, Cm, Inches, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import io
import requests
import mistletoe
# --- 修复点：这里去掉了 s，改为单数 ---
from mistletoe import block_token, span_token
from mistletoe.base_renderer import BaseRenderer

# ==========================================
# 部分 1: 核心底层 XML 操作 - 实现完美背景图
# ==========================================
def insert_bg_xml(part, r_id):
    """
    构造 VML XML 代码，用于定义一个铺满全屏的背景图片。
    """
    vmldata = f"""<v:background id="_x0000_s1025" o:bwmode="white" fillcolor="white [3212]" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<v:fill r:id="{r_id}" type="frame"/>
</v:background>"""
    bg_element = OxmlElement.from_xml(vmldata)
    part.element.insert(0, bg_element)

def set_true_background(doc, image_stream):
    """
    将图片设置为文档所有章节的真正背景。
    """
    document_part = doc.part
    image_part = document_part.relate_to(image_stream, docx.opc.constants.RELATIONSHIP_TYPE.IMAGE)
    r_id = image_part.rId

    for section in doc.sections:
        section_element = section._sectPr
        insert_bg_xml(section_element, r_id)
        
    # 设置页边距：根据你的 Huamai 模板（左侧有红色条），
    # 我们需要把左边距设大一点，避开那个Logo区域
    sections = doc.sections
    for section in sections:
        section.top_margin = Cm(3.0)      # 上边距避开Logo
        section.bottom_margin = Cm(2.0)   # 下边距
        section.left_margin = Cm(2.5)     # 左边距（根据你的图示，这里可能需要调整）
        section.right_margin = Cm(2.0)    # 右边距

# ==========================================
# 部分 2: 自定义 Markdown 渲染器
# ==========================================
class DocxRenderer(BaseRenderer):
    def __init__(self, doc):
        self.doc = doc
        # 设置正文字体
        style = doc.styles['Normal']
        font = style.font
        font.name = '微软雅黑'
        font.size = Pt(10.5)
        # 必须显式设置中文字体
        font._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
        super().__init__()

    def render_document(self, token):
        for child in token.children:
            self.render(child)

    def render_heading(self, token):
        level = token.level
        text = self.render_inner(token)
        # 添加标题
        p = self.doc.add_heading(text, level=level)
        # 稍微调整标题间距
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(6)

    def render_paragraph(self, token):
        paragraph = self.doc.add_paragraph()
        self.render_inner(token, paragraph)

    def render_raw_text(self, token, parent_paragraph=None):
        if parent_paragraph:
            run = parent_paragraph.add_run(token.content)
            # 确保中文字体正确显示
            run.font.name = '微软雅黑'
            run._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
            return run
        return token.content

    def render_strong(self, token, parent_paragraph):
        run = self.render_inner(token, parent_paragraph)
        if run: run.bold = True

    def render_emphasis(self, token, parent_paragraph):
        run = self.render_inner(token, parent_paragraph)
        if run: run.italic = True
        
    def render_list(self, token):
        for child in token.children:
            # 修复：使用 block_token
            self.render(child, list_style='List Bullet' if not token.start else 'List Number')

    def render_list_item(self, token, list_style):
        # 修复：使用 block_token.Paragraph
        if len(token.children) > 0 and isinstance(token.children[0], block_token.Paragraph):
             paragraph = self.doc.add_paragraph(style=list_style)
             self.render_inner(token.children[0], paragraph)
        else:
             for child in token.children:
                 self.render(child)

    def render_image(self, token, parent_paragraph):
        url = token.src
        alt_text = token.title if token.title else (token.children[0].content if token.children else "")
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            image_stream = io.BytesIO(response.content)
            
            run = parent_paragraph.add_run()
            run.add_picture(image_stream, width=Cm(14)) # 限制宽度
            if alt_text:
                parent_paragraph.add_run(f"\n{alt_text}").italic = True
        except Exception:
             run = parent_paragraph.add_run(f"[图片加载失败: {alt_text}]")
             run.font.color.rgb = RGBColor(255, 0, 0)

    def render_table(self, token):
        # 修复表格乱码问题：使用真正的 Word 表格
        rows = len(token.children)
        if rows == 0: return
        cols = len(token.children[0].children)
        
        table = self.doc.add_table(rows=rows, cols=cols)
        table.style = 'Table Grid' 

        for i, row_token in enumerate(token.children):
            row = table.rows[i]
            for j, cell_token in enumerate(row_token.children):
                cell = row.cells[j]
                cell._element.clear_content()
                paragraph = cell.add_paragraph()
                self.render_inner(cell_token, paragraph)

    def render_inner(self, token, parent_paragraph=None):
        if hasattr(token, 'children'):
            last_run = None
            for child in token.children:
                # 修复：使用 span_token 单数
                if isinstance(child, span_token.RawText):
                    last_run = self.render_raw_text(child, parent_paragraph)
                elif isinstance(child, span_token.Strong):
                    self.render_strong(child, parent_paragraph)
                elif isinstance(child, span_token.Emphasis):
                    self.render_emphasis(child, parent_paragraph)
                elif isinstance(child, span_token.Image):
                    self.render_image(child, parent_paragraph)
            return last_run
        return token.content

# ==========================================
# 部分 3: Streamlit 主界面
# ==========================================
st.set_page_config(page_title="Huamai 文档生成器", layout="wide")

st.title("📄 Huamai Markdown 转 Word (修复版)")
st.markdown("该版本修复了 `ImportError`，并针对你的图片模板优化了背景对齐和表格显示。")

col1, col2 = st.columns([4, 6])

with col1:
    st.subheader("1. 上传背景模板")
    bg_file = st.file_uploader("请上传你的 HUAMAI A4 底图", type=['png', 'jpg', 'jpeg'])
    
    st.subheader("3. 生成")
    generate_btn = st.button("🚀 生成文档", type="primary", use_container_width=True)

with col2:
    st.subheader("2. 输入内容")
    default_md = """# HUAMAI 产品规格书

## 1. 产品简介
本产品采用高品质材质...

## 2. 技术参数
| 指标 | 参数值 | 备注 |
| :--- | :--- | :--- |
| 阻抗 | 50 Ohms | 标准 |
| 频率 | DC-6GHz | 宽频 |
"""
    md_input = st.text_area("Markdown 内容", height=500, value=default_md)

if generate_btn:
    if not md_input.strip():
        st.error("请先输入内容！")
    else:
        with st.spinner("正在生成..."):
            try:
                doc = Document()
                if bg_file:
                    image_stream = io.BytesIO(bg_file.getvalue())
                    set_true_background(doc, image_stream)

                renderer = DocxRenderer(doc)
                doc_token = mistletoe.Document(md_input)
                renderer.render(doc_token)
                
                doc_io = io.BytesIO()
                doc.save(doc_io)
                doc_io.seek(0)
                
                st.success("成功！")
                st.download_button(
                    label="📥 下载 Word 文档",
                    data=doc_io,
                    file_name="Huamai_Spec.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    type="primary"
                )
            except Exception as e:
                st.error(f"错误: {str(e)}")
