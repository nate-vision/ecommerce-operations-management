"""Generate report tables, figures and example outputs from recorded CSVs and Olist.
Copy this script and results/customer/raw into the project; run from project root:
  python scripts/generate_customer_results.py
No benchmark timings are fabricated or re-run by this script.
"""
from pathlib import Path
import sys
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results' / 'customer'
RAW = OUT / 'raw'
ORDER = ['Q1_baseline','Q1_optimized','Q2','Q3','Q4','Q5','Q6']
FILES = {'Stage 2':'customer_benchmark_stage2.csv', 'After restructuring':'customer_benchmark_restructured.csv', 'Local':'customer_benchmark_local.csv'}

def summarize():
    summaries=[]
    for label, filename in FILES.items():
        data=pd.read_csv(RAW/filename)
        if set(data['query'])!=set(ORDER) or data.duplicated(['query','run']).any() or data['elapsed_ms'].le(0).any() or data['elapsed_ms'].isna().any():
            raise ValueError(f'Invalid timing file: {filename}')
        if not data.groupby('query').size().eq(9).all() or not data.groupby('query')['rows'].nunique().eq(1).all():
            raise ValueError(f'Expected nine runs and stable row counts: {filename}')
        if data.sqlite_version.nunique()!=1:
            raise ValueError('Mixed SQLite versions')
        s=data.groupby('query').agg(runs=('run','count'),rows=('rows','first'),median_ms=('elapsed_ms','median'),min_ms=('elapsed_ms','min'),max_ms=('elapsed_ms','max')).reindex(ORDER).reset_index()
        s.insert(0,'sqlite_version',data.sqlite_version.iloc[0]); s.insert(0,'experiment',label)
        summaries.append(s)
    summary=pd.concat(summaries,ignore_index=True)
    summary.to_csv(OUT/'benchmark_summary.csv',index=False,float_format='%.6f')
    speed=[]
    for label in FILES:
        t=summary[summary.experiment==label].set_index('query')
        b,o=t.loc['Q1_baseline','median_ms'],t.loc['Q1_optimized','median_ms']
        speed.append({'experiment':label,'sqlite_version':t.sqlite_version.iloc[0],'baseline_ms':b,'optimized_ms':o,'speedup':b/o,'time_reduction_pct':(1-o/b)*100})
    speed=pd.DataFrame(speed); speed.to_csv(OUT/'q1_comparison.csv',index=False,float_format='%.6f')
    return summary,speed

def plot(summary,speed):
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':150})
    charts=OUT/'charts'; charts.mkdir(exist_ok=True)
    fig,ax=plt.subplots(figsize=(7.5,3.2)); y=range(len(speed))
    for i,r in speed.iterrows():
        ax.plot([r.optimized_ms,r.baseline_ms],[i,i],color='#a8b3bd',lw=2,zorder=1)
        ax.annotate(f'{r.speedup:,.0f}×',((r.optimized_ms*r.baseline_ms)**.5,i),xytext=(0,7),textcoords='offset points',ha='center',fontsize=9)
    ax.scatter(speed.baseline_ms,y,label='Baseline',color='#777777',s=45,zorder=3)
    ax.scatter(speed.optimized_ms,y,label='Optimized',color='#176b91',s=45,zorder=3)
    ax.set_xscale('log'); ax.set_xlim(.15,3500); ax.set_yticks(list(y),speed.experiment); ax.invert_yaxis(); ax.set_ylim(2.45,-.45); ax.set_xlabel('Median SQL execution time (ms, log scale)'); ax.grid(axis='x',alpha=.2); ax.legend(loc='lower center',bbox_to_anchor=(.5,1.01),ncol=2,frameon=False); fig.tight_layout(); fig.savefig(charts/'q1_comparison.png',dpi=300,bbox_inches='tight'); plt.close(fig)
    t=summary[(summary.experiment=='Local') & (summary['query']!='Q1_baseline')].copy()
    labels=['Q1 List','Q2 Search','Q3 Details','Q4 History','Q5 Summary','Q6 Items']
    fig,ax=plt.subplots(figsize=(7.5,3.2)); y=range(6)
    ax.barh(list(y),t.median_ms,color='#176b91',height=.57)
    ax.errorbar(t.median_ms,list(y),xerr=[t.median_ms-t.min_ms,t.max_ms-t.median_ms],fmt='none',ecolor='#434343',capsize=3,lw=1)
    for i,(_,r) in enumerate(t.iterrows()): ax.text(r.max_ms+.023,i,f'{r.median_ms:.3f}',va='center',fontsize=9)
    ax.set_yticks(list(y),labels); ax.invert_yaxis(); ax.set_xlim(0,1.08); ax.set_xlabel('SQL execution time (ms)'); ax.grid(axis='x',alpha=.2); ax.set_axisbelow(True); fig.tight_layout(); fig.savefig(charts/'local_query_latency.png',dpi=300,bbox_inches='tight'); plt.close(fig)

def examples():
    sys.path.insert(0,str(ROOT))
    from modules.customer import customer_module as cm
    e=OUT/'query_examples'; e.mkdir(exist_ok=True)
    cid,oid=cm.SAMPLE_CUSTOMER,cm.SAMPLE_ORDER
    results={'Q1_customer_list':cm.get_customers(),'Q2_customer_search':cm.search_customers('8d50f5','SP'),'Q3_customer_details':cm.get_customer_details(cid),'Q4_order_history':cm.get_customer_orders(cid),'Q5_customer_summary':cm.get_customer_summary(cid),'Q6_order_items':cm.get_order_items(cid,oid)}
    for name,df in results.items(): df.to_csv(e/f'{name}.csv',index=False)
    print('Example query row counts:',{k:len(v) for k,v in results.items()})

if __name__=='__main__':
    summary,speed=summarize(); plot(summary,speed); examples(); print(speed.to_string(index=False))
