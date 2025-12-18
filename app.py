import streamlit as st
import io
import requests

# --- 调试与安全导入模块 ---
try:
    import docx
    from docx import Document
    from docx.shared import Pt, Cm, RGBColor
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    
    # 使用全路径导入 mistletoe，防止路径混淆
    import mistletoe
    import mistletoe.block_token as block_token
    import mistletoe.span_token as span_token
    from mistletoe.base_renderer import BaseRenderer
    
except ImportError as e:
    st.error("🚨 库导入失败！请检查 requirements.txt 或仓库中是否有同名文件冲突。")
    st.code(f"详细错误: {str(e)}")
    st.stop()
except Exception as e:
    st.error(f"🚨 发生未知错误: {str(e)}")
    st.stop()

# ==========================================
# 核心功能区
# ==========================================

def set_true_background(doc, image_stream):
    """设置 Word 文档底层背景"""
    try:
        document_part = doc.part
        image_part = document_part.relate_to(image_stream, docx.opc.constants.RELATIONSHIP_TYPE.IMAGE)
        r_id = image_part.rId

        # 构造 VML XML
        vmldata = f"""<v:background id="_x0000_s1025" o:bwmode="white" fillcolor="white [3212]" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
        <v:fill r:id="{r_id}" type="frame"/>
        </v:background>"""
        
        # 应用到所有章节
        for section in doc.sections:
            section_element = section._sectPr
            bg_element = OxmlElement.from_xml(vmldata)
            # 防止重复插入
            if section_element.find(qn('v:background')) is None:
                section_element.insert(0, bg_element)
            
            # 设置页边距以避开背景图的Logo区域 (根据你的A4设计调整)
            section.top_margin = Cm(3.0)      
            section.bottom_margin = Cm(2.0)
            section.left_margin = Cm(2.5)
            section.right_margin = Cm(2.0)
            
    except Exception as e:
        st.warning(f"背景图设置出现小问题，但不影响文档生成: {e}")

class DocxRenderer(BaseRenderer):
    """自定义 Markdown 渲染器"""
    def __init__(self, doc):
        self.doc = doc
        # 优化中文字体设置
        style = doc.styles['Normal']
        font = style.font
        font.name = '微软雅黑'
        font.size = Pt(10.5)
        font._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
        # mistletoe 解析入口
        super().__init__()

    def render_document(self, token):
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
        for child in token.children:
            self.render(child, list_style='List Bullet' if not token.start else 'List Number')

    def render_list_item(self, token, list_style):
        # 兼容性处理：不同版本的mistletoe结构可能细微不同
        if hasattr(token, 'children') and len(token.children) > 0:
            first_child = token.children[0]
            # 检查是否为段落
            if isinstance(first_child, block_token.Paragraph):
                paragraph = self.doc.add_paragraph(style=list_style)
                self.render_inner(first_child, paragraph)
            else:
                # 直接渲染其他内容
                for child in token.children:
                    self.render(child)

    def render_image(self, token, parent_paragraph):
        url = token.src
        alt_text = token.title if token.title else (token.children[0].content if token.children and hasattr(token.children[0], 'content') else "图片")
        
        try:
            # 下载图片
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            image_stream = io.BytesIO(response.content)
            
            run = parent_paragraph.add_run()
            run.add_picture(image_stream, width=Cm(14))
            if alt_text:
                parent_paragraph.add_run(f"\n{alt_text}").italic = True
        except Exception:
             run = parent_paragraph.add_run(f"[图片无法加载: {alt_text}]")
             run.font.color.rgb = RGBColor(255, 0, 0)

    def render_table(self, token):
        if not hasattr(token, 'children'): return
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
# 界面逻辑
# ==========================================
st.set_page_config(page_title="Huamai 文档生成器", layout="wide", page_icon="📄")

st.title("📄 Huamai 文档生成工具 (稳定版)")
st.caption("v2.0 - 修复了导入错误，优化了表格和背景图支持")

col1, col2 = st.columns([4, 6])

with col1:
    st.info("💡 提示：请确保你上传的图片是 A4 尺寸 (210x297mm)")
    bg_file = st.file_uploader("1. 上传背景图 (PNG/JPG)", type=['png', 'jpg', 'jpeg'])
    generate_btn = st.button("🚀 生成 Word 文档", type="primary", use_container_width=True)

with col2:
    default_md = """# HUAMAI 产品规格书

## 1. 产品简介
本产品采用高品质材质...

## 2. 技术参数
| 指标 | 参数值 | 备注 |
| :--- | :--- | :--- |
| 阻抗 | 50 Ohms | 标准 |
| 频率 | DC-6GHz | 宽频 |

## 3. 测试图片
![测试图](https://via.placeholder.com/150)
"""
    md_input = st.text_area("2. 输入 Markdown 内容", height=500, value=default_md)

if generate_btn:
    if not md_input.strip():
        st.error("请输入内容！")
    else:
        with st.spinner("文档生成中..."):
            try:
                # 1. 准备文档
                doc = Document()
                if bg_file:
                    image_stream = io.BytesIO(bg_file.getvalue())
                    set_true_background(doc, image_stream)

                # 2. 解析Markdown
                renderer = DocxRenderer(doc)
                doc_token = mistletoe.Document(md_input)
                renderer.render(doc_token)
                
                # 3. 输出
                doc_io = io.BytesIO()
                doc.save(doc_io)
                doc_io.seek(0)
                
                st.success("✅ 生成成功！")
                st.download_button(
                    label="📥 点击下载 .docx",
                    data=doc_io,
                    file_name="Huamai_Spec_Final.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    type="primary"
                )
            except Exception as e:
                st.error(f"❌ 生成过程中出错: {e}")
                import traceback
                st.code(traceback.format_exc())
