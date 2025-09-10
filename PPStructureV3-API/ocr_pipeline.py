from pathlib import Path
from paddleocr import PPStructureV3

pipeline = PPStructureV3()  # 初始化一次，复用

def pdf_to_markdown(input_file: str, output_dir: str):
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    output = pipeline.predict(input=input_file)

    markdown_list = []
    markdown_images = []

    for res in output:
        md_info = res.markdown
        markdown_list.append(md_info)
        markdown_images.append(md_info.get("markdown_images", {}))

    markdown_texts = pipeline.concatenate_markdown_pages(markdown_list)

    mkd_file_path = output_path / f"{Path(input_file).stem}.md"
    with open(mkd_file_path, "w", encoding="utf-8") as f:
        f.write(markdown_texts)

    for item in markdown_images:
        if item:
            for path, image in item.items():
                file_path = output_path / path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                image.save(file_path)

    return mkd_file_path
