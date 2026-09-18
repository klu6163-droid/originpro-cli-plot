"""User-supplied defaults for ordinary XY curves and existing peak-fit curves.

Only presentation is generated here. Different X arrays retain their acquisition order;
net-to-display transformations must already exist in the confirmed job and provenance.
"""
from __future__ import annotations
import math
import os
import re
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))
from origin_text import origin_rich_text

PRESETS = {'ordinary_curve', 'peak_deconvolution'}


def compile_mapping(job, style):
    """Preflight and deterministic plot/auxiliary mapping; never launches Origin."""
    graph = job['graph']
    preset = style.get('curve_preset')
    if preset not in PRESETS:
        raise ValueError('Unknown curve preset')
    if not graph.get('x_label') or not graph.get('y_label'):
        raise ValueError('Curve presets require explicit axis titles with actual units.')
    if not re.fullmatch(r'[\w .-]{1,100}', style['font_family']):
        raise ValueError('Invalid font name')
    series = graph['series']
    fields, columns = job['_fields'], job['_columns']
    mappings, peak_index = [], 0
    for i, entry in enumerate(series):
        x = entry.get('x_column', graph['x_column'])
        y = entry['y_column']
        if not isinstance(x, int) or not 0 <= x < len(fields) or x == y:
            raise ValueError(f'Invalid X/Y pairing for curve {i+1}')
        pairs = [(a,b) for a,b in zip(columns[fields[x]], columns[fields[y]]) if math.isfinite(a) and math.isfinite(b)]
        if len(pairs) < 2:
            raise ValueError(f'Curve {i+1} has fewer than two finite X/Y pairs')
        if any(k in entry for k in ('y_error', 'x_error', 'error_column')):
            raise ValueError('Use the error-bar route for declared uncertainty; this executor is plain XY.')
        role = entry.get('role', 'sample')
        component = role == 'component' or re.fullmatch(r'component\d+', role) is not None
        if preset == 'ordinary_curve':
            default = style['curve_palette'][i] if i < len(style['curve_palette']) else None
            line_style = 0
        elif component:
            default = style['component_palette'][peak_index] if peak_index < len(style['component_palette']) else None
            peak_index += 1
            line_style = 0
        else:
            if role not in style['series']:
                raise ValueError(f'Peak preset requires explicit raw/fit/component/background roles: {role}')
            default = style['series'][role]['color']
            line_style = style['series'][role]['line_style']
        color = entry.get('color', default)
        if not color or not re.fullmatch(r'#[0-9a-fA-F]{6}', color):
            raise ValueError('Supply a distinct explicit HEX color when the default palette is exhausted.')
        name = entry.get('name') or job['worksheet']['columns'][y].get('long_name') or fields[y]
        item = {'plot': len(mappings)+1, 'source_series': i, 'x_column': x, 'y_column': y,
                'name': name, 'role': role, 'auxiliary': False, 'color': color,
                'line_style': entry.get('line_style', line_style),
                'line_width_pt': entry.get('line_width', style['line_width_pt'])}
        if not isinstance(item['line_width_pt'],(int,float)) or not 0 < item['line_width_pt'] <= 100:
            raise ValueError('line_width must be a positive point value')
        if not isinstance(item['line_style'],int) or not 0 <= item['line_style'] <= 10:
            raise ValueError('line_style must be an Origin style index from 0 to 10')
        if component and preset == 'peak_deconvolution':
            target = entry.get('fill_to_y_column')
            mode = graph.get('component_mode')
            if mode not in ('includes_background', 'baseline_subtracted'):
                raise ValueError('Declare component_mode: includes_background or baseline_subtracted. For net peaks, prepare display=S+B columns with provenance before confirmation.')
            if not isinstance(target, int) or not 0 <= target < len(fields) or target in (x,y):
                raise ValueError(f'Component {name} needs an explicit fill_to_y_column (own background or documented zero baseline).')
            tx = entry.get('fill_x_column', x)
            if not isinstance(tx, int) or not 0 <= tx < len(fields):
                raise ValueError('Invalid fill_x_column')
            if tx != x:
                raise ValueError('Gradient pairing currently requires the same X column. Retain independent grids and use a separately verified renderer; do not silently interpolate.')
            usable = [(a,b,c) for a,b,c in zip(columns[fields[x]],columns[fields[y]],columns[fields[target]])
                      if all(math.isfinite(v) for v in (a,b,c))]
            if len(usable) < 2:
                raise ValueError('No common valid X interval for gradient fill')
            xx = [r[0] for r in usable]
            diffs = [b-a for a,b in zip(xx,xx[1:])]
            if not (all(d>0 for d in diffs) or all(d<0 for d in diffs)):
                raise ValueError('Peak fill needs a monotonic X grid; do not sort loop/cycle data automatically.')
            if mode == 'baseline_subtracted' and any(v != 0 for v in columns[fields[target]] if math.isfinite(v)):
                raise ValueError('baseline_subtracted requires an explicit zero display baseline.')
            if mode == 'includes_background' and not any(s.get('role')=='background' and s['y_column']==target for s in series):
                raise ValueError('Fill target must be the declared target-data background curve.')
            item['fill_target_plot'] = item['plot']+1
            mappings.append(item)
            mappings.append({'plot': len(mappings)+1, 'source_series': i, 'x_column': tx,
                             'y_column': target, 'name': name+' fill reference', 'role': 'fill_reference',
                             'auxiliary': True, 'color': '#808080', 'line_style': 0, 'line_width_pt': 3})
        else:
            mappings.append(item)
    if preset == 'peak_deconvolution' and not peak_index:
        raise ValueError('No component curves: use ordinary_curve for an unsplit spectrum.')
    units={re.sub(r'\s+','',job['worksheet']['columns'][m['y_column']].get('units','')).casefold()
           for m in mappings if not m['auxiliary']}
    if len(units-{''})>1:
        raise ValueError('Different Y units cannot share this axis without an explicit conversion or separate plot.')
    signatures = [(m['color'].lower(),m['line_style']) for m in mappings if not m['auxiliary'] and (preset=='ordinary_curve' or 'fill_target_plot' in m)]
    if len(signatures) != len(set(signatures)):
        raise ValueError('Repeated curve colors/line styles: provide distinguishable mappings.')
    return mappings


def nice_step(span):
    raw = abs(span)/6
    if raw <= 0: return 1
    scale = 10**math.floor(math.log10(raw))
    return min((1,2,2.5,5,10), key=lambda k:abs(k-raw/scale))*scale


def fit_consistency(job, mapping):
    """Report the existing curve sum; enforce only a declared data-precision tolerance."""
    fit=next((m for m in mapping if m['role']=='fit'),None)
    parts=[m for m in mapping if 'fill_target_plot' in m]
    if not fit or not parts: return {'status':'not_applicable'}
    if any(m['x_column']!=fit['x_column'] for m in parts):
        return {'status':'not_checked','reason':'Independent grids; no interpolation was performed.'}
    cols=job['_columns'];fields=job['_fields']
    backgrounds={mapping[m['fill_target_plot']-1]['y_column'] for m in parts}
    if len(backgrounds)!=1: return {'status':'not_checked','reason':'Multiple baselines; declare the intended sum separately.'}
    bcol=next(iter(backgrounds))
    arrays=[cols[fields[fit['y_column']]],cols[fields[bcol]]]+[cols[fields[m['y_column']]] for m in parts]
    pairs=[]
    for row in zip(*arrays):
        if all(math.isfinite(v) for v in row):
            expected=sum(row[2:])-(len(parts)-1)*row[1]
            pairs.append((row[0],expected))
    if not pairs: return {'status':'not_checked','reason':'No common finite rows.'}
    result={'status':'residual_reported','common_rows':len(pairs),
            'max_absolute_residual':max(abs(a-b) for a,b in pairs),
            'meaning':'Numerical consistency of supplied curves; not a validation of fit model or peak assignment.'}
    tolerance=job['graph'].get('fit_tolerance')
    if tolerance:
        atol=float(tolerance.get('atol',0));rtol=float(tolerance.get('rtol',0))
        if atol<0 or rtol<0:raise ValueError('Fit consistency tolerances must be nonnegative')
        result.update(tolerance=tolerance,pass_=all(abs(a-b)<=atol+rtol*abs(b) for a,b in pairs))
        if not result['pass_']:raise ValueError('Supplied fit and component/background sum exceed the declared tolerance.')
    return result


def configure(op, job, sheet, graph_page, layer, style):
    from delivery_contract import write
    from originpro_build import axis_range
    from origin_readback import snapshot, compare
    mapping = compile_mapping(job, style)
    consistency=fit_consistency(job,mapping)
    graph = job['graph']
    # Presets have one simple XY layer; do not resize arbitrary retained multi-panel templates.
    if len(list(graph_page)) != 1 or len(list(op.pages('g'))) != 1:
        raise ValueError('Curve presets require one graph/one layer; complex templates need explicit per-layer mapping.')
    for plot in reversed(list(layer.plot_list())): plot.remove()
    graph_page.activate();layer.activate()
    expected = {}
    def prop(expr, value, path):
        if not op.lt_exec(f'{expr}={value};'):
            raise RuntimeError(f'Origin rejected {expr}')
        expected[path] = value
    graph_page.obj.PutWidth(style['page_width_mm']/25.4)
    graph_page.obj.PutHeight(style['page_height_mm']/25.4)
    expected['g1/width_mm'],expected['g1/height_mm'] = style['page_width_mm'],style['page_height_mm']
    op.lt_exec('page.updatetoprinter=0;page.kar=0;')
    prop('page.connect',0,'g1/connect_missing')
    prop('page.basecolor',int(op.lt_float('color(255,255,255)')),'g1/basecolor')
    for key,value in {'unit':1,'factor':1,**style['layer_geometry']}.items():
        prop('layer.'+key,value,'g1/l1/geometry/'+key)
    prop('layer.tickw',style['frame_width_pt'],'g1/l1/tick_width')
    font = int(op.lt_float(f"font({style['font_family']})"))
    if font <= 1: raise RuntimeError('Font unavailable: '+style['font_family'])
    show_y = graph.get('show_y_tick_labels',style['show_y_tick_labels'])
    for axis in ('x','y','x2','y2'):
        prefix='g1/l1/axis/'+axis+'/'
        active = axis=='x' or (axis=='y' and show_y)
        props={'showAxes':3, 'showGrids':0, 'thickness':style['frame_width_pt'], 'color':1,
               'showlabel':int(active), 'ticks':10 if active else 0, 'minorTicks':1,
               'ticklength':style['major_tick_length_pt'],
               'mticklength':style['minor_tick_length_pt'],
               'tickthickness':style['frame_width_pt'],'mtickthickness':style['frame_width_pt'],
               'label.font':font,'label.pt':style['tick_label_size_pt'],
               'label.bold':0,'label.rotate':0,'label.color':1}
        for key,value in props.items(): prop(f'layer.{axis}.{key}',value,prefix+key)
    fields, cols = job['_fields'],job['_columns']
    xv=[x for m in mapping if not m['auxiliary'] for x,y in zip(cols[fields[m['x_column']]],cols[fields[m['y_column']]]) if math.isfinite(x) and math.isfinite(y)]
    yv=[y for m in mapping for x,y in zip(cols[fields[m['x_column']]],cols[fields[m['y_column']]]) if math.isfinite(x) and math.isfinite(y)]
    reverse=graph.get('reverse_x',graph.get('spectrum_type','').lower()=='xps')
    xr=axis_range(graph.get('x_from'),graph.get('x_to'),xv,reverse=reverse)
    yr=axis_range(graph.get('y_from'),graph.get('y_to'),yv,padding_fraction=style['y_padding_fraction'])
    for axis, limits in [('x',xr),('y',yr)]:
        scale=graph.get(axis+'_scale','linear')
        if scale not in ('linear','log10'): raise ValueError('Use a dedicated route for this axis scale')
        if scale=='log10' and (min(limits)<=0 or min(xv if axis=='x' else yv)<=0):
            raise ValueError('Log axis needs positive data and limits')
        layer.axis(axis).scale=scale
        layer.axis(axis).limits=(limits[0],limits[1],graph.get(axis+'_step',nice_step(limits[1]-limits[0]) if scale=='linear' else 1))
        for key,value in zip(('from','to'),limits): expected[f'g1/l1/axis/{axis}/{key}']=value
    for name in ('XT','YR'):
        if layer.label(name): layer.label(name).remove()
    for axis,name in [('x','XB'),('y','YL')]:
        layer.axis(axis).title=origin_rich_text(graph[axis+'_label'])
        label=layer.label(name)
        for key,value in [('font',font),('fsize',style['axis_title_size_pt']),('color',1),('rotate',90 if axis=='y' else 0),('attach',1)]:
            label.set_float(key,value)
            expected[f'g1/l1/text/{name}/{key}']=value
        label.set_int('show',1)
    for item in mapping:
        p=layer.add_plot(sheet,coly=item['y_column'],colx=item['x_column'],type='l')
        p.color=item['color']
        p.set_cmd(f"-wp {item['line_width_pt']}",f"-d {item['line_style']}",f"-l {0 if item['auxiliary'] else 1}",'-pf 0')
        prefix=f"g1/l1/p{item['plot']}/"
        color=int(op.lt_float('color('+','.join(str(int(item['color'][i:i+2],16)) for i in (1,3,5))+')'))
        for k,v in {'type':200,'line_color':color,'line_width_units':item['line_width_pt']*500,
                    'line_style':item['line_style'],'line_connect':0 if item['auxiliary'] else 1,
                    'fill_enabled':int('fill_target_plot' in item)}.items(): expected[prefix+k]=v
        if 'fill_target_plot' in item:
            p.set_cmd('-pf 1','-pfv 8','-pfn 1','-pfm 3',f'-pfb {color}',
                      '-pff color(255,255,255)','-lfp 0')
            for k,v in {'fill_mode':8,'fill_common_x':1,'gradient_mode':3,'fill_color':color,
                        'gradient_end_color':int(op.lt_float('color(255,255,255)')),'fill_target_offset':0}.items(): expected[prefix+k]=v
    expected['g1/l1/plot_count']=len(mapping)
    legend=graph.get('legend',style['legend'])
    if legend=='auto': legend=len(graph['series'])>1
    if layer.label('legend'): layer.label('legend').remove()
    if legend:
        op.lt_exec('legend;')
        label=layer.label('legend')
        label.text='\n'.join('\\l('+str(m['plot'])+') '+m['name'] for m in mapping if not m['auxiliary'])
        for key,value in [('font',font),('fsize',style['legend_size_pt']),('background',0),('color',1),('attach',1)]:
            label.set_float(key,value)
            expected['g1/l1/text/'+label.obj.Name+'/'+key]=value
    # Rendering resolves text extents; position titles in page units against the final axes.
    out=Path(os.environ.get('ORIGINPRO_DELIVERY_DIR',job['_output_opju'].parent))
    graph_page.save_fig(str(out/'curve-layout-preview.png'),type='png',replace=True,width=800)
    pw,ph=op.lt_float('page.width'),op.lt_float('page.height')
    xb,yl=layer.label('XB'),layer.label('YL')
    for lb,left,top in [(xb,pw*0.52-xb.get_float('width')/2,ph*0.925),
                        (yl,pw*0.035,ph*0.46-yl.get_float('height')/2)]:
        lb.set_float('left',left);lb.set_float('top',top)
    if legend:
        lb=layer.label('legend');geo=style['layer_geometry']
        # Minimize data points covered by the actual legend rectangle across four corners.
        width,height=lb.get_float('width')/pw*100,lb.get_float('height')/ph*100
        candidates=[(geo['left']+2,geo['top']+2),(geo['left']+geo['width']-width-2,geo['top']+2),
                    (geo['left']+2,geo['top']+geo['height']-height-2),
                    (geo['left']+geo['width']-width-2,geo['top']+geo['height']-height-2)]
        def occupied(pos):
            count=0
            for m in mapping:
                if m['auxiliary']:continue
                for x,y in zip(cols[fields[m['x_column']]],cols[fields[m['y_column']]]):
                    if not math.isfinite(x) or not math.isfinite(y):continue
                    px=geo['left']+(x-xr[0])/(xr[1]-xr[0])*geo['width']
                    py=geo['top']+(1-(y-yr[0])/(yr[1]-yr[0]))*geo['height']
                    count+=int(pos[0]<=px<=pos[0]+width and pos[1]<=py<=pos[1]+height)
            return count
        left,top=min(candidates,key=occupied)
        lb.set_float('left',pw*left/100);lb.set_float('top',ph*top/100)
    graph_page.save_fig(str(out/'curve-layout-preview.png'),type='png',replace=True,width=1800)
    state=snapshot(op)
    checked=compare(expected,state,subset=True)
    report={'preset':style['curve_preset'],'scientific_curve_count':len(graph['series']),
            'auxiliary_curve_count':sum(m['auxiliary'] for m in mapping),'mapping':mapping,
            'expected':expected,'style_check':checked,'fit_consistency':consistency,
            'implementation_choices':style.get('implementation_choices',[])}
    write(out/'curve-style-report.json',report)
    if not checked['pass']:
        failed=[r for r in checked['checks'] if not r['pass']]
        raise RuntimeError('Curve preset readback failed: '+str(failed))
    return {'worksheet_rows':int(sheet.rows),'worksheet_columns':int(sheet.cols),
            'plot_count':len(mapping),'x_range':xr,'y_range':yr,'template_mode':job['_template_opju'] is not None}
