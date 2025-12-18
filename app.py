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
# 核心设置区
# ==========================================

def setup_page_layout(doc, image_stream=None):
    """
    统一设置页面布局：A4尺寸、精确边距、背景图
    """
    # 1. 准备背景图关联 (如果有)
    bg_rId = None
    if image_stream:
        try:
            # 关键：重置文件指针，防止读取为空
            image_stream.seek(0)
            # 获取或添加图片，返回 rId (如 "rId4")
            bg_rId, _ = doc.part.get_or_add_image(image_stream)
        except Exception as e:
            st.error(f"背景图处理失败: {e}")

    # 2. 遍历所有章节进行设置
    for section in doc.sections:
        # --- A. 设置 A4 尺寸 ---
        section.page_width = Cm(21.0)
        section.page_height = Cm(29.7)
        
        # --- B. 设置用户指定的精确边距 ---
        # 上:72pt 下:72pt 左:54pt 右:54pt
        section.top_margin = Pt(72)
        section.bottom_margin = Pt(72)
        section.left_margin = Pt(54)
        section.right_margin = Pt(54)

        # --- C. 设置背景图 (VML) ---
        if bg_rId:
            section_element = section._sectPr
            # 构造 VML XML
            # fill type="frame" 会自动拉伸图片填满纸张
            vmldata = f"""<v:background id="_x0000_s1025" o:bwmode="white" fillcolor="white [3212]" 
                          xmlns:v="urn:schemas-microsoft-com:vml" 
                          xmlns:o="urn:schemas-microsoft-com:office:office">
                <v:fill r:id="{bg_rId}" type="frame"/>
            </v:background>"""
            
            # 清除旧背景（如果有）并插入新背景
            existing_bg = section_element.find(qn('v:background'))
            if existing_bg is not None:
                section_element.remove(existing_bg)
            
            bg_element = OxmlElement.from_xml(vmldata)
            section_element.insert(0, bg_element)

# ==========================================
# Markdown 渲染器
# ==========================================

class DocxRenderer(BaseRenderer):
    def __init__(self, doc):
        self.doc = doc
        # 设置正文字体
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
        # 标题间距优化
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
        list_style = 'List Number' if token.start else 'List Bullet'
        if hasattr(token, 'children') and token.children:
            for list_item in token.children:
                if hasattr(list_item, 'children') and list_item.children:
                    first_child = list_item.children[0]
                    paragraph = self.doc.add_paragraph(style=list_style)
                    if isinstance(first_child, block_token.Paragraph):
                        self.render_inner(first_child, paragraph)
                    else:
                        self.render_inner(first_child, paragraph)

    def render_list_item(self, token): 
        pass 

    def render_image(self, token, parent_paragraph):
        url = token.src
        alt_text = token.title if token.title else "图片"
        
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            image_stream = io.BytesIO(response.content)
            
            run = parent_paragraph.add_run()
            # 限制 markdown 内嵌图片宽度，防止撑破页面
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

st.title("📄 Huamai 文档生成工具 (V5.0 精确版)")
st.markdown("""
**本次更新：**
1. 📐 **强制 A4 尺寸** (210mm x 297mm)
2. 📏 **精确页边距** (上72pt, 下72pt, 左54pt, 右54pt)
3. 🖼️ **修复背景图丢失问题**
""")

col1, col2 = st.columns([4, 6])

with col1:
    st.info("💡 请上传 A4 尺寸背景图")
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
"""
    md_input = st.text_area("Markdown 内容", height=500, value=default_md)

if generate_btn:
    if not md_input.strip():
        st.error("请输入 Markdown 内容！")
    else:
        with st.spinner("正在排版..."):
            try:
                # 1. 创建文档
                doc = Document()
                
                # 2. 渲染 Markdown 内容
                # 注意：先渲染内容，再应用布局，确保布局应用到所有生成的章节
                renderer = DocxRenderer(doc)
                doc_token = mistletoe.Document(md_input)
                renderer.render(doc_token)
                
                # 3. 应用布局 (A4, 边距, 背景图)
                # 传入背景图片流
                bg_stream = io.BytesIO(bg_file.getvalue()) if bg_file else None
                setup_page_layout(doc, bg_stream)
                
                # 4. 保存
                doc_io = io.BytesIO()
                doc.save(doc_io)
                doc_io.seek(0)
                
                st.success("✅ 生成成功！背景图和边距已应用。")
                st.download_button(
                    label="📥 下载最终文档 (A4)",
                    data=doc_io,
                    file_name="Huamai_A4_Spec.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    type="primary"
                )
            except Exception as e:
                st.error(f"❌ 错误: {e}")
                import traceback
                st.code(traceback.format_exc())
