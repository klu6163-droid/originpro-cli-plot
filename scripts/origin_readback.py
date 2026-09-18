"""Read actual Origin objects, compare saved state, and export the reopened project."""
from __future__ import annotations
import math
import os
import sys
from pathlib import Path
from delivery_contract import digest, read, write

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))
from origin_text import origin_rich_text


def number(value):
    value = float(value)
    return value if math.isfinite(value) else None


def clean_data(value):
    if hasattr(value, 'tolist'):
        value = value.tolist()
    if isinstance(value, (list, tuple)):
        return [clean_data(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return {'missing': str(value)}
    return value


def plot_option(op, plot, option, layer=None):
    # Clear first: unsupported properties must not reuse a previous LabTalk result.
    try:
        target = plot if isinstance(plot,str) else plot.lt_range()
        parent = layer.obj if layer is not None else plot.layer
        ok = parent.LT_execute(f'__delivery_v=NA();{{range rr={target};get rr {option} __delivery_v;}}')
        return number(op.lt_float('__delivery_v')) if ok else None
    except (SystemError, RuntimeError):
        # Some options are not applicable to every native plot. Requested properties
        # still fail closed in compare(expected, actual); unsupported ones stay explicit.
        return None


def snapshot(op):
    state, unavailable = {}, []
    def put(key, value, required=False):
        if value is None:
            unavailable.append(key)
            if required:
                raise RuntimeError(f'Required Origin readback unavailable: {key}')
        else:
            state[key] = value
    graphs = list(op.pages('g'))
    put('graph_count', len(graphs))
    if not graphs:
        raise RuntimeError('Project has no graph pages')
    for gi, graph in enumerate(graphs, 1):
        graph.activate()
        op.lt_exec('doc -uw;')
        gp = f'g{gi}'
        put(f'{gp}/name', graph.name)
        put(f'{gp}/width_mm', number(graph.obj.GetWidth() * 25.4), True)
        put(f'{gp}/height_mm', number(graph.obj.GetHeight() * 25.4), True)
        for key, prop in [('connect_missing','connect'),('basecolor','basecolor')]:
            put(f'{gp}/{key}', number(op.lt_float(f'page.{prop}')))
        layers = list(graph)
        put(f'{gp}/layer_count', len(layers))
        for li, layer in enumerate(layers, 1):
            layer.activate()
            lp = f'{gp}/l{li}'
            put(f'{lp}/tick_width',number(op.lt_float('layer.tickw')))
            for key in ('unit', 'left', 'top', 'width', 'height', 'factor'):
                put(f'{lp}/geometry/{key}', number(op.lt_float(f'layer.{key}')), True)
            for axis in ('x', 'y', 'x2', 'y2', 'z', 'z2'):
                for key in ('from', 'to', 'inc', 'type', 'showLabels', 'label.font', 'label.pt',
                            'showAxes','showGrids','showlabel','ticks','minorTicks',
                            'thickness','color','ticklength','mticklength','tickthickness','mtickthickness',
                            'label.bold','label.rotate','label.color'):
                    put(f'{lp}/axis/{axis}/{key}', number(op.lt_float(f'layer.{axis}.{key}')),
                        axis in ('x', 'y') and key in ('from', 'to', 'label.font', 'label.pt'))
            for obj in layer.obj.GraphObjects:
                label = layer.label(obj.Name)
                if obj.Name.upper().startswith('SPECTRUM'):
                    for prop in ('labels.font', 'labels.fsize', 'title', 'show', 'left', 'top', 'width', 'height'):
                        put(f'{lp}/colorbar/{obj.Name}/{prop}', number(op.lt_float(f'{obj.Name}.{prop}')), True)
                text = str(obj.Text)
                font = number(label.get_float('font'))
                size = number(label.get_float('fsize'))
                # Internal Origin graph objects also appear in GraphObjects; include actual text objects.
                if text or (font is not None and font > 0 and size is not None and size > 0):
                    key = f'{lp}/text/{obj.Name}'
                    put(f'{key}/text', text)
                    put(f'{key}/font', font, bool(text))
                    put(f'{key}/fsize', size, bool(text))
                    put(f'{key}/show', bool(obj.GetShow()))
                    for prop in ('attach','color','background'):
                        put(f'{key}/{prop}',number(label.get_float(prop)))
                    # Hidden auto-titles can resolve their text lazily on open. Their font is checked,
                    # but their unrendered bounding rectangle is not a persisted layout contract.
                    if obj.GetShow():
                        for prop in ('left', 'top', 'width', 'height', 'rotate'):
                            put(f'{key}/{prop}', number(label.get_float(prop)))
            # Read the collection count directly and address plots by range; iterating
            # COM DataPlots after a redraw can omit the last item or yield stale pointers.
            plot_count = int(layer.obj.DataPlots.Count) if getattr(op,'oext',False) else len(layer.plot_list())
            put(f'{lp}/plot_count', plot_count)
            for pi in range(1,plot_count+1):
                pp = f'{lp}/p{pi}'
                # Stable page/layer/plot ranges avoid stale COM DataPlot pointers after
                # Origin redraws a graph. Values still come from the live project.
                plot = f'[{graph.name}]{li}!{pi}'
                for axis in ('X', 'Y'):
                    # @R can return ### for reopened Origin 2025 columns with long names.
                    # Dataset ID + first/last plotted rows gives the same binding without that formatter.
                    binding = []
                    for option in ('@D', '@RB', '@RE'):
                        op.set_lt_str('__delivery_range', '')
                        ok = layer.obj.LT_execute(f'string __delivery_range$ = "%({pi}{axis},{option})";')
                        value = op.get_lt_str('__delivery_range')
                        if not ok or not value or value == '###':
                            raise RuntimeError(f'Cannot read plot data binding: {pp}/{axis}/{option}')
                        binding.append(value)
                    put(f'{pp}/{axis.lower()}_range', binding)
                dataset_name = state[f'{pp}/y_range'][0]
                put(f'{pp}/dataset',dataset_name)
                for key, option in {'type': '-pt', 'line_color': '-c', 'line_width_units': '-w',
                                    'fill_enabled': '-pf', 'fill_color': '-pfb', 'fill_pattern': '-pfp',
                                    'data_label_font': '-tf', 'data_label_size': '-ts',
                                    'line_style':'-d','line_connect':'-l'}.items():
                    put(f'{pp}/{key}', plot_option(op, plot, option,layer))
                # Origin's -lfp accesses a target plot; asking it on a non-filled final
                # curve can leave OriginExt with a native GetIndex exception.
                if state.get(f'{pp}/type') == 200 and state.get(f'{pp}/fill_enabled') == 1:
                    for key,option in {'fill_mode':'-pfv','fill_common_x':'-pfn','gradient_mode':'-pfm',
                                       'gradient_end_color':'-pff'}.items():
                        put(f'{pp}/{key}',plot_option(op,plot,option,layer))
                    if state.get(f'{pp}/fill_mode') in (8,9):
                        put(f'{pp}/fill_target_offset',plot_option(op,plot,'-lfp',layer))
                put(f'{pp}/transparency', number(layer.get_float(f'plot{pi}.transparency')))
                if dataset_name.lower().startswith('mbook'):
                    for key, option in (('cell_label_font', '-qf'), ('cell_label_size', '-qs')):
                        put(f'{pp}/{key}', plot_option(op, plot, option,layer), True)
    # Hash complete worksheet and matrix values, not a preview of the first rows.
    for kind in ('w', 'm'):
        books = list(op.pages(kind))
        put(f'{kind}_book_count', len(books))
        for bi, book in enumerate(books, 1):
            for si, sheet in enumerate(book, 1):
                prefix = f'{kind}{bi}/s{si}'
                if kind == 'w':
                    arrays = [clean_data(sheet.to_list(c)) for c in range(sheet.cols)]
                    put(f'{prefix}/cols', int(sheet.cols))
                else:
                    arrays = clean_data(sheet.to_np3d())
                put(f'{prefix}/name', sheet.name)
                put(f'{prefix}/data_sha256', digest(arrays))
    return {'values': state, 'unavailable_optional_properties': sorted(unavailable)}


def compare(expected, actual, *, subset=False):
    e = expected.get('values', expected)
    a = actual.get('values', actual)
    rows = []
    for key in sorted(e if subset else set(e) | set(a)):
        ev, av = e.get(key), a.get(key)
        tolerance = 0.0
        if isinstance(ev, (float, int)) and not isinstance(ev, bool):
            tolerance = 0.3 if key.endswith(('/width_mm', '/height_mm')) else (0.05 if any(
                p in key for p in ('/geometry/', '/fsize', '/left', '/top', '/width', '/height')) else 1e-7 * max(1, abs(ev)))
            passed = isinstance(av, (int, float)) and abs(ev-av) <= tolerance
        else:
            passed = key in e and key in a and ev == av
        rows.append({'property': key, 'expected': ev, 'actual': av, 'tolerance': tolerance, 'pass': passed})
    return {'pass': all(r['pass'] for r in rows), 'checks': rows}


def preservation_expectations(template, job, profile):
    """Preserve styling outside the explicitly requested edits to the first graph/layer."""
    result = {}
    selected_style = read(job['graph']['style_file']) if job['graph'].get('style_file') else {}
    curve_preset = selected_style.get('curve_preset')
    for key, value in template['values'].items():
        keep = '/geometry/' in key or key.endswith(('/width_mm', '/height_mm', '/layer_count', '/font', '/fsize', '/label.font', '/label.pt'))
        if curve_preset and (key.startswith('g1/l1/') or key in ('g1/width_mm','g1/height_mm')):
            keep = False
        if 'font_family' in profile and key.endswith(('/font', '/label.font')):
            keep = False
        if 'font_size_pt' in profile and key.endswith(('/fsize', '/label.pt')):
            keep = False
        if 'page_width_mm' in profile and key.endswith(('/width_mm', '/height_mm')):
            keep = False
        # A deliberately removed legend is absent, not a failed font.
        if '/text/legend/' in key.lower() and not job['graph'].get('legend', True):
            keep = False
        if keep:
            result[key] = value
    return result


def apply_profile(op, profile):
    requested = dict(profile.get('expected', {}))
    family = profile.get('font_family')
    font = int(op.lt_float(f'font({family})')) if family else None
    if family and font <= 1:
        raise RuntimeError(f'Origin could not resolve requested font: {family}')
    for gi, graph in enumerate(op.pages('g'), 1):
        # Detached color scales use absolute page units; keep their page fractions when resizing.
        colorbars = []
        graph.activate()
        page_w, page_h = op.lt_float('page.width'), op.lt_float('page.height')
        for layer in graph:
            layer.activate()
            for obj in layer.obj.GraphObjects:
                if obj.Name.upper().startswith('SPECTRUM'):
                    colorbars.append((layer, obj.Name, {k: op.lt_float(f'{obj.Name}.{k}') / (page_w if k in ('left','width') else page_h)
                                                       for k in ('left','top','width','height')}))
        if 'page_width_mm' in profile:
            graph.activate()
            op.lt_exec('page.updatetoprinter=0;page.kar=0;')
            graph.obj.PutWidth(profile['page_width_mm']/25.4)
            graph.obj.PutHeight(profile['page_height_mm']/25.4)
            requested[f'g{gi}/width_mm'] = profile['page_width_mm']
            requested[f'g{gi}/height_mm'] = profile['page_height_mm']
        for li, layer in enumerate(graph, 1):
            layer.activate()
            prefix = f'g{gi}/l{li}'
            for axis in ('x', 'y', 'x2', 'y2', 'z', 'z2'):
                if number(op.lt_float(f'layer.{axis}.from')) is None:
                    continue
                for key, val in (('label.font', font), ('label.pt', profile.get('font_size_pt'))):
                    if val is not None:
                        op.lt_exec(f'layer.{axis}.{key}={val};')
                        requested[f'{prefix}/axis/{axis}/{key}'] = val
            for obj in layer.obj.GraphObjects:
                label = layer.label(obj.Name)
                size = number(label.get_float('fsize'))
                if not obj.Text and not (size is not None and size > 0):
                    continue
                text = str(obj.Text)
                formatted = origin_rich_text(text)
                if formatted != text:
                    label.text = formatted
                    requested[f'{prefix}/text/{obj.Name}/text'] = formatted
                for key, val in (('font', font), ('fsize', profile.get('font_size_pt'))):
                    if val is not None:
                        label.set_float(key, val)
                        requested[f'{prefix}/text/{obj.Name}/{key}'] = val
            for pi, plot in enumerate(layer.plot_list(), 1):
                if str(plot.obj.GetDatasetName()).lower().startswith('mbook'):
                    for key, option, val in (('cell_label_font', '-qf', font), ('cell_label_size', '-qs', profile.get('font_size_pt'))):
                        if val is not None:
                            plot.set_cmd(f'{option} {val}')
                            requested[f'{prefix}/p{pi}/{key}'] = val
        for layer, name, fractions in colorbars:
            layer.activate()
            for prop, val in (('labels.font',font), ('labels.fsize',profile.get('font_size_pt'))):
                if val is not None:
                    op.lt_exec(f'{name}.{prop}={val};')
                    requested[f'g{gi}/l{layer.index()+1}/colorbar/{name}/{prop}'] = val
            if 'page_width_mm' in profile:
                # Size/font changes can recenter Origin color scales. Assign position last.
                for prop in ('width', 'height', 'left', 'top'):
                    dimension = 'width' if prop in ('left', 'width') else 'height'
                    op.lt_exec(f'{name}.{prop}=page.{dimension}*{fractions[prop]:.12g};')
    return requested


def install_save_hook(op, directory, refresh_layout=False):
    """Capture renderer state immediately before its real save, without changing vendor code."""
    original = op.save
    def captured(*args, **kwargs):
        if refresh_layout:
            # Native templates can carry stale auto-title extents after worksheet replacement.
            # A real render resolves Origin's text layout before the persisted-state baseline.
            for gi, graph in enumerate(op.pages('g'), 1):
                graph.save_fig(str(Path(directory)/f'layout-preview-{gi}.png'), type='png', replace=True, width=640)
        write(Path(directory)/'before-save.json', snapshot(op))
        return original(*args, **kwargs)
    op.save = captured
    return original


def export_all(op, directory, profile):
    directory = Path(directory)
    results = []
    for gi, graph in enumerate(op.pages('g'), 1):
        graph.activate()
        stem = 'result' if gi == 1 else f'result_graph{gi}'
        for fmt in ('png', 'pdf', 'tif'):
            extra = 'tr2.PDF.Fonts.Embed:=1 tr2.PDF.Fonts.TrueType:=1' if fmt == 'pdf' else (
                f'tr2.{fmt.upper()}.dotsperinch:={profile["dpi"]} tr2.{fmt.upper()}.bitsperpixel:="24-bit Color"')
            if fmt == 'tif':
                extra += f' tr2.TIF.Compression:="{profile["tiff_compression"]}"'
            # The directory is controlled staging; reject LabTalk metacharacters before interpolation.
            if any(c in str(directory) for c in ('"', '\n', '\r')):
                raise ValueError('Unsupported export path characters')
            target = directory / f'{stem}.{fmt}'
            if target.exists():
                target.unlink()
            cmd = (f'expGraph type:={fmt} export:=page filename:="{stem}" path:="{directory.as_posix()}" '
                   f'overwrite:=replace sysopts:=0 keepsize:=1 tr.Margin:=2 {extra};')
            if not op.lt_exec(cmd) or not target.is_file() or target.stat().st_size == 0:
                raise RuntimeError(f'Origin export failed: {target.name}')
            results.append({'graph': gi, 'format': fmt, 'path': str(target),
                            'width_mm': graph.obj.GetWidth()*25.4,
                            'height_mm': graph.obj.GetHeight()*25.4})
    return results
