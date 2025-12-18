import streamlit as st
import io
import requests

# --- 导入处理 ---
try:
    import docx
    from docx import Document
    from docx.shared import Pt, Cm, RGBColor
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    
    import mistletoe
    from mistletoe import block_token, span_token
    from mistletoe.base_renderer import BaseRenderer
    
except ImportError as e:
    st.error(f"🚨 依赖库导入失败: {e}")
    st.stop()

# ==========================================
# 核心修复区：背景图与保存逻辑
# ==========================================

def set_true_background(doc, image_stream):
    """
    设置 Word 文档底层背景
    修复了 AttributeError: '_io.BytesIO' object has no attribute 'rels'
    """
    try:
        document_part = doc.part
        
        # [核心修复点] 
        # 不能直接用 relate_to(stream)，必须用 get_or_add_image(stream)
        # 它会正确创建 ImagePart 并返回 (rId, image_part)
        r_id, _ = document_part.get_or_add_image(image_stream)

        # 构造 VML XML (定义背景)
        vmldata = f"""<v:background id="_x0000_s1025" o:bwmode="white" fillcolor="white [3212]" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
        <v:fill r:id="{r_id}" type="frame"/>
        </v:background>"""
        
        for section in doc.sections:
            section_element = section._sectPr
            if section_element.find(qn('v:background')) is None:
                bg_element = OxmlElement.from_xml(vmldata)
                section_element.insert(0, bg_element)
            
            # 页边距调整 (避开左侧红色 Logo)
            section.top_margin = Cm(2.5)      
            section.bottom_margin = Cm(2.0)
            section.left_margin = Cm(3.0) 
            section.right_margin = Cm(2.0)
            
    except Exception as e:
        print(f"背景设置警告: {e}")
        # 这里不抛出异常，防止阻断保存

# ==========================================
# 渲染器逻辑
# ==========================================

class DocxRenderer(BaseRenderer):
    """自定义 Markdown 渲染器"""
    def __init__(self, doc):
        self.doc = doc
        style = doc.styles['Normal']
        font = style.font
        font.name = '微软雅黑'
        font.size = Pt(10.5)
        font._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
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

    def render_paragraph(self, token):
        paragraph = self.doc.add_paragraph()
        self.render_inner(token, paragraph)

    def render_raw_text(self, token, parent_paragraph=None):
        content = token.content
        if parent_paragraph:
            run = parent_paragraph.add_run(content)
            run.font.name = '微软雅黑'
            run._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
            return run
        return content

    def render_strong(self, token, parent_paragraph):
        run = self.render_inner(token, parent_paragraph)
        if run: run.bold = True

    def render_emphasis(self, token, parent_paragraph):
        run = self.render_inner(token, parent_paragraph)
        if run: run.italic = True
        
    def render_list(self, token):
        # 1. 确定列表样式
        list_style = 'List Number' if token.start else 'List Bullet'
        
        # 2. 遍历列表项，手动处理，避免传递非法参数
        if hasattr(token, 'children') and token.children:
            for list_item in token.children:
                if hasattr(list_item, 'children') and list_item.children:
                    first_child = list_item.children[0]
                    # 创建带样式的段落
                    paragraph = self.doc.add_paragraph(style=list_style)
                    # 渲染内容
                    if isinstance(first_child, block_token.Paragraph):
                        self.render_inner(first_child, paragraph)
                    else:
                        self.render_inner(first_child, paragraph)

    def render_list_item(self, token): 
        # 由 render_list 接管，此处留空
        pass 

    def render_image(self, token, parent_paragraph):
        url = token.src
        alt_text = "图片"
        if hasattr(token, 'title') and token.title:
            alt_text = token.title
        elif hasattr(token, 'children') and token.children and hasattr(token.children[0], 'content'):
            alt_text = token.children[0].content
        
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            image_stream = io.BytesIO(response.content)
            
            run = parent_paragraph.add_run()
            run.add_picture(image_stream, width=Cm(14))
            parent_paragraph.add_run(f"\n{alt_text}").italic = True
        except Exception:
             run = parent_paragraph.add_run(f"[图片加载失败: {alt_text}]")
             run.font.color.rgb = RGBColor(255, 0, 0)

    def render_table(self, token):
        if not hasattr(token, 'children') or not token.children: return
        rows = len(token.children)
        if rows == 0: return
        if not hasattr(token.children[0], 'children') or not token.children[0].children: return
        cols = len(token.children[0].children)
        
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

st.title("📄 Huamai 文档生成工具 (V4.0)")

col1, col2 = st.columns([4, 6])

with col1:
    st.info("💡 请上传 A4 背景图")
    bg_file = st.file_uploader("上传背景图 (PNG/JPG)", type=['png', 'jpg', 'jpeg'])
    generate_btn = st.button("🚀 生成 Word 文档", type="primary", use_container_width=True)

with col2:
    default_md = """# HUAMAI 产品规格书

## 1. 产品简介
本产品采用高品质材质...

## 2. 列表测试
* 特性 A
* 特性 B

## 3. 技术参数
| 指标 | 参数值 | 备注 |
| :--- | :--- | :--- |
| 阻抗 | 50 Ohms | 标准 |
| 频率 | DC-6GHz | 宽频 |
"""
    md_input = st.text_area("Markdown 内容", height=500, value=default_md)

if generate_btn:
    if not md_input.strip():
        st.error("请输入 Markdown 内容！")
    else:
        with st.spinner("文档处理中..."):
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
                
                st.success("✅ 生成成功！")
                st.download_button(
                    label="📥 点击下载 Result.docx",
                    data=doc_io,
                    file_name="Huamai_Product_Spec.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    type="primary"
                )
            except Exception as e:
                st.error(f"❌ 错误: {e}")
                import traceback
                st.code(traceback.format_exc())
