import copy
import csv
import json
from pathlib import Path
import sys
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import delivery_contract as dc
from originpro_build import validate_job
from curve_presets import compile_mapping, fit_consistency
from origin_readback import compare


@pytest.fixture
def peak(tmp_path):
    data=tmp_path/'data.csv'
    data.write_text('x,raw,fit,p1,p2,bg,x2\n1,8,8,4,5,1,3\n2,10,10,5,6,1,2\n3,8,8,4,5,1,1\n')
    style=dc.read(ROOT/'assets/peak_deconvolution_style.json')
    job={'data_csv':str(data),'output_opju':str(tmp_path/'out.opju'),
         'worksheet':{'columns':[{'field':k,'units':'eV' if k in ('x','x2') else 'a.u.'} for k in ['x','raw','fit','p1','p2','bg','x2']]},
         'graph':{'x_column':0,'x_label':'Binding Energy (eV)','y_label':'Intensity (a.u.)',
                  'style_file':str(ROOT/'assets/peak_deconvolution_style.json'),
                  'component_mode':'includes_background','fit_tolerance':{'atol':1e-6},
                  'series':[{'y_column':1,'role':'raw'},{'y_column':2,'role':'fit'},
                            {'y_column':3,'role':'component','fill_to_y_column':5},
                            {'y_column':4,'role':'component','fill_to_y_column':5},
                            {'y_column':5,'role':'background'}]}}
    path=tmp_path/'job.json';dc.write(path,job)
    return path,job,style


def test_background_helpers_rebuilt_for_actual_peak_count(peak):
    path,_,style=peak
    m=compile_mapping(validate_job(path),style)
    assert len(m)==7
    assert [x['plot'] for x in m if x['auxiliary']]==[4,6]
    for component in [x for x in m if 'fill_target_plot' in x]:
        helper=m[component['fill_target_plot']-1]
        assert helper['y_column']==5 and helper['x_column']==0
        assert helper['plot']==component['plot']+1


@pytest.mark.parametrize('mode',['net','unknown',None])
def test_unknown_background_mode_rejected_before_origin(peak,mode):
    path,job,_=peak;job['graph']['component_mode']=mode;dc.write(path,job)
    with pytest.raises(ValueError,match='component_mode'):validate_job(path)


def test_different_fill_grid_not_silently_interpolated(peak):
    path,job,_=peak;job['graph']['series'][2]['fill_x_column']=6;dc.write(path,job)
    with pytest.raises(ValueError,match='same X column'):validate_job(path)


def test_background_not_added_twice(peak):
    path,job,style=peak
    assert fit_consistency(validate_job(path),compile_mapping(validate_job(path),style))['max_absolute_residual']==0
    data=Path(job['data_csv']);data.write_text(data.read_text().replace('1,8,8,4,5,1,3','1,8,8,5,6,1,3'))
    with pytest.raises(ValueError,match='sum exceed'):validate_job(path)


def test_zero_baseline_must_be_zero(peak):
    path,job,_=peak;job['graph']['component_mode']='baseline_subtracted';dc.write(path,job)
    with pytest.raises(ValueError,match='explicit zero'):validate_job(path)


def test_independent_curve_x_and_acquisition_order_preserved(peak):
    path,job,_=peak;job['graph']['style_file']=str(ROOT/'assets/ordinary_curve_style.json')
    job['graph']['series']=[{'y_column':1,'x_column':6,'name':'Sample A'},{'y_column':2,'x_column':0,'name':'Sample B'}]
    dc.write(path,job);normalized=validate_job(path)
    m=compile_mapping(normalized,dc.read(job['graph']['style_file']))
    assert [p['x_column'] for p in m]==[6,0]
    assert normalized['_columns']['x2']==[3,2,1]
    assert not any(p['auxiliary'] or 'fill_target_plot' in p for p in m)


def test_style_source_hash_is_bound_and_cosmetics_reuse_consent(peak):
    path,job,_=peak;record=dc.prepare('native',path)
    assert any(f['role']=='style_spec' for f in record['files'])
    record=dc.confirm(record,'Synthetic fixture consent','pytest','test_fixture')
    job['graph']['series'][0]['line_style']=2;dc.write(path,job)
    new=dc.prepare('native',path,reuse=record)
    assert new['science_sha256']==record['science_sha256']
    job['graph']['series'][2]['fill_to_y_column']=4;dc.write(path,job)
    with pytest.raises(ValueError):dc.prepare('native',path,reuse=record)


def test_palette_exhaustion_requires_explicit_distinct_mapping(peak):
    path,job,_=peak
    job['graph']['style_file']=str(ROOT/'assets/ordinary_curve_style.json')
    job['graph']['series']=[{'y_column':1,'name':f'Sample {i}'} for i in range(8)]
    dc.write(path,job)
    with pytest.raises(ValueError,match='palette is exhausted'):validate_job(path)


def test_incompatible_units_require_explicit_conversion(peak):
    path,job,_=peak;job['worksheet']['columns'][4]['units']='mA';dc.write(path,job)
    with pytest.raises(ValueError,match='Different Y units'):validate_job(path)
