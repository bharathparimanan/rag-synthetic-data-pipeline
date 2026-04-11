from src.models.schema import ParsedChunk

def parse_pdf(
        source_file:str
) -> list[ParsedChunk]:
    print("parse_pdf")