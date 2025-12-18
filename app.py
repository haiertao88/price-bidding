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
    
    # 显式导入 mistletoe 模块
    import mistletoe
    from mistletoe import block_token, span_token
    from mistletoe.base_renderer import BaseRenderer
    
except ImportError as e:
    st.error(f"🚨 依赖库导入失败: {e}")
    st.info("请检查 requirements.txt 是否包含: mistletoe==1.0.1")
    st.stop()

# ==========================================
# 核心功能修复区
# ==========================================

def set_true_background(doc, image_stream):
    """设置 Word 文档底层背景 (修复 rId 字符串问题)"""
    try:
        document_part = doc.part
        
        # [修复点 1] 获取关系 ID
        # relate_to 可能直接返回字符串 ID (如 "rId4")，也可能返回对象
        rel_result = document_part.relate_to(image_stream, docx.opc.constants.RELATIONSHIP_TYPE.IMAGE)
        
        if isinstance(rel_result, str):
            r_id = rel_result
        elif hasattr(rel_result, 'rId'):
            r_id = rel_result.rId
        else:
            r_id = str(rel_result) # 兜底策略

        # 构造 VML XML (定义背景)
        vmldata = f"""<v:background id="_x0000_s1025" o:bwmode="white" fillcolor="white [3212]" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
        <v:fill r:id="{r_id}" type="frame"/>
        </v:background>"""
        
        # 应用到所有章节
        for section in doc.sections:
            section_element = section._sectPr
            # 避免重复添加
            if section_element.find(qn('v:background')) is None:
                bg_element = OxmlElement.from_xml(vmldata)
                section_element.insert(0, bg_element)
            
            # [调整页边距] 配合你的左侧红色 Logo 条
            # 稍微加大左边距，防止文字压在红条上
            section.top_margin = Cm(2.5)      
            section.bottom_margin = Cm(2.0)
            section.left_margin = Cm(3.0)  # 左侧留宽一点
            section.right_margin = Cm(2.0)
            
    except Exception as e:
        print(f"背景设置警告: {e}")
        # 不抛出错误，以免阻断主流程，只是背景图可能失败

class DocxRenderer(BaseRenderer):
    """自定义 Markdown 渲染器 (修复 NoneType 错误)"""
    def __init__(self, doc):
        self.doc = doc
        # 设置中文字体
        style = doc.styles['Normal']
        font = style.font
        font.name = '微软雅黑'
        font.size = Pt(10.5)
        font._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
        super().__init__()

    def render_document(self, token):
        # [修复点 2] 增加防空检查
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
        if hasattr(token, 'children') and token.children:
            for child in token.children:
                self.render(child, list_style='List Bullet' if not token.start else 'List Number')

    def render_list_item(self, token, list_style):
        if hasattr(token, 'children') and token.children:
            first_child = token.children[0]
            if isinstance(first_child, block_token.Paragraph):
                paragraph = self.doc.add_paragraph(style=list_style)
                self.render_inner(first_child, paragraph)
            else:
                for child in token.children:
                    self.render(child)

    def render_image(self, token, parent_paragraph):
        url = token.src
        # 安全获取 title 或 alt
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
        # [修复点 3] 表格渲染的强壮性检查
        if not hasattr(token, 'children') or not token.children: 
            return
            
        rows = len(token.children)
        if rows == 0: return
        
        # 检查第一行是否存在且有子元素
        if not hasattr(token.children[0], 'children') or not token.children[0].children:
            return
            
        cols = len(token.children[0].children)
        
        table = self.doc.add_table(rows=rows, cols=cols)
        table.style = 'Table Grid' 

        for i, row_token in enumerate(token.children):
            row = table.rows[i]
            if hasattr(row_token, 'children') and row_token.children:
                for j, cell_token in enumerate(row_token.children):
                    if j < len(row.cells): # 防止越界
                        cell = row.cells[j]
                        cell._element.clear_content()
                        paragraph = cell.add_paragraph()
                        self.render_inner(cell_token, paragraph)

    def render_inner(self, token, parent_paragraph=None):
        # [核心修复] 递归渲染时的防空检查
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

st.title("📄 Huamai 文档生成工具 (Fix v3.0)")

col1, col2 = st.columns([4, 6])

with col1:
    st.info("💡 请上传你的背景底图")
    bg_file = st.file_uploader("上传背景图 (PNG/JPG)", type=['png', 'jpg', 'jpeg'])
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
![示例图](https://via.placeholder.com/150)
"""
    md_input = st.text_area("Markdown 内容", height=500, value=default_md)

if generate_btn:
    if not md_input.strip():
        st.error("请输入 Markdown 内容！")
    else:
        with st.spinner("文档处理中..."):
            try:
                doc = Document()
                # 1. 应用背景
                if bg_file:
                    image_stream = io.BytesIO(bg_file.getvalue())
                    set_true_background(doc, image_stream)

                # 2. 解析内容
                renderer = DocxRenderer(doc)
                doc_token = mistletoe.Document(md_input)
                renderer.render(doc_token)
                
                # 3. 导出
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
                st.error(f"❌ 依然报错: {e}")
                import traceback
                st.code(traceback.format_exc())
