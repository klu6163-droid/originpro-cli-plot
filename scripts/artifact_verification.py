"""Inspect exported file contents; missing or unreadable output is a failure."""
from pathlib import Path
from delivery_contract import file_record


def inspect_export(item, profile):
    from PIL import Image
    path = Path(item['path'])
    report = file_record(path, item['format'])
    failures = []
    def check(ok, message):
        if not ok:
            failures.append(message)
    if item['format'] in ('png', 'tif'):
        with Image.open(path) as image:
            image.load()
            check(image.format == {'png': 'PNG', 'tif': 'TIFF'}[item['format']], 'Wrong image format')
            expected = [round(item[k]/25.4*profile['dpi']) for k in ('width_mm', 'height_mm')]
            check(all(abs(a-b) <= 3 for a,b in zip(image.size, expected)), 'Pixel dimensions differ from physical size/DPI')
            dpi = image.info.get('dpi')
            check(dpi is not None and all(abs(float(v)-profile['dpi']) < 1 for v in dpi), 'DPI metadata mismatch')
            report.update(pixels=list(image.size), expected_pixels=expected, dpi=[float(v) for v in dpi] if dpi else None)
            if item['format'] == 'tif':
                compression = int(image.tag_v2.get(259, 1))
                check(compression == {'None': 1, 'LZW': 5, 'PackBits': 32773}[profile['tiff_compression']], 'TIFF compression mismatch')
                report['compression_tag'] = compression
    else:
        from pypdf import PdfReader
        from pypdf.generic import ContentStream
        pdf = PdfReader(path)
        check(len(pdf.pages) == 1, 'Expected one PDF page per graph')
        page = pdf.pages[0]
        dimensions = [float(page.mediabox.width)/72*25.4, float(page.mediabox.height)/72*25.4]
        check(all(abs(a-b) <= 0.5 for a,b in zip(dimensions, [item['width_mm'], item['height_mm']])), 'PDF page dimensions mismatch')
        fonts, images, vectors = [], [], 0
        seen = set()
        def resources(res):
            res = res.get_object()
            for name, ref in res.get('/Font', {}).items():
                font = ref.get_object()
                children = font.get('/DescendantFonts', [font])
                embedded = True
                for child in children:
                    descriptor = child.get_object().get('/FontDescriptor')
                    embedded &= bool(descriptor and any(k in descriptor.get_object() for k in ('/FontFile', '/FontFile2', '/FontFile3')))
                fonts.append({'resource': str(name), 'name': str(font.get('/BaseFont', '')), 'embedded': embedded})
            for name, ref in res.get('/XObject', {}).items():
                obj = ref.get_object()
                key = getattr(ref, 'idnum', id(obj))
                if key in seen:
                    continue
                seen.add(key)
                if obj.get('/Subtype') == '/Image':
                    images.append({'name': str(name), 'width': obj.get('/Width'), 'height': obj.get('/Height')})
                if '/Resources' in obj:
                    resources(obj['/Resources'])
        resources(page['/Resources'])
        stream = ContentStream(page.get_contents(), pdf)
        vectors = sum(op in (b'm', b'l', b'c', b're') for _, op in stream.operations)
        text = page.extract_text() or ''
        check(not profile['pdf_text_required'] or bool(text.strip()), 'PDF has no extractable text')
        check(not profile['pdf_embedded_fonts_required'] or (bool(fonts) and all(f['embedded'] for f in fonts)), 'PDF fonts are missing or unembedded')
        # A raster-only PDF is blocked. Mixed heatmaps/text are allowed and explicitly reported.
        raster_only = bool(images) and (not text.strip() or vectors == 0)
        check(profile['allow_full_page_raster'] or not raster_only, 'PDF appears raster-only')
        report.update(page_count=len(pdf.pages), size_mm=dimensions, fonts=fonts,
                      text_characters=len(text), image_objects=images, vector_path_operators=vectors,
                      raster_only=raster_only,
                      limitation='Mixed raster/vector figures still require visual inspection; this is not a pixel-equivalence proof.')
    report.update(pass_=not failures, failures=failures)
    return report
