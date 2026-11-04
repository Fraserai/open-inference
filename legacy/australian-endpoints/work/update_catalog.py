from pathlib import Path
import json
root=Path('/Users/caeseyfraser/Documents/Codex/2026-09-13/ai/outputs/australian-endpoints')
p=root/'app/config.py';s=p.read_text().replace('MODELS = [','CONNECTION_MODELS = [',1)
rows=[
('glm-5-3','GLM-5.3','max',45),('kimi-k3','Kimi K3','max',44),('glm-5-3-flash','GLM-5.3-Flash','',42),
('qwen3-8-2-4t-a95b','Qwen3.8 2.4T A95B','',40),('deepseek-v4-1-flash','DeepSeek V4.1 Flash','max',40),
('deepseek-v4-pro-0813','DeepSeek V4 Pro 0813','max',36),('qwen3-8-27b','Qwen3.8 27B','xhigh',34),
('k2-horizon-375b-a23b','K2 Horizon 375B A23B','',31),('minimax-m3','MiniMax-M3','',30),
('inkling','Inkling','',26),('nemotron-3-ultra','Nemotron 3 Ultra','',23),('muse-glimmer','Muse Glimmer','high',18),
('mistral-medium-3-5','Mistral Medium 3.5','',15),('gpt-oss-120b','gpt-oss-120B','high',12)]
models=[dict(id='mock/'+slug,name=name,evaluation_setting=setting,score=score,chart_order=i+1,estimated=slug.startswith('k2-horizon'),revision='',hf_repository=None,live_eligible=False) for i,(slug,name,setting,score) in enumerate(rows)]
addition='''# Transcribed from the user-supplied chart, not a live leaderboard fetch.
# mock/* values are local catalog IDs, never claimed Hugging Face repository IDs.
CATALOG_SOURCE = {
    "title": "Artificial Analysis Intelligence Index — Open Source Models",
    "date": "2026-09-12",
    "version": "4.3",
    "provenance": "User-supplied screenshot; date from filename",
    "scores": "Displayed integer scores, not unrounded source data",
}
MODELS = '''+repr(models)+'\n'
s=s.replace('PROVIDERS = [',addition+'\nPROVIDERS = [');p.write_text(s)
p=root/'app/main.py';s=p.read_text().replace('from .config import MODELS, PROVIDERS, STATIC, Settings','from .config import CATALOG_SOURCE, CONNECTION_MODELS, MODELS, PROVIDERS, STATIC, Settings')
s=s.replace('"instance": "ml.g6.2xlarge",','"instance": None if d["model"].startswith("mock/") else "ml.g6.2xlarge",')
s=s.replace('"models": MODELS,','"models": MODELS if settings.mode == "mock" else CONNECTION_MODELS,\n            "source": CATALOG_SOURCE if settings.mode == "mock" else None,')
s=s.replace('for m in MODELS if m["id"] == data.model','for m in MODELS + CONNECTION_MODELS if m["id"] == data.model')
s=s.replace('            if not provider.preflight()["ready"]:', '            if model not in CONNECTION_MODELS:\n                raise HTTPException(422, "This model is mock-only: repository, licence, runtime and GPU sizing are unverified")\n            if not provider.preflight()["ready"]:')
p.write_text(s)
p=root/'tests/test_aws_adapter.py';s=p.read_text().replace('from app.config import MODELS, Settings','from app.config import CONNECTION_MODELS as MODELS\nfrom app.config import Settings');p.write_text(s)
p=root/'app/static/index.html';s=p.read_text().replace('Supported, pinned Hugging Face models.','Your Artificial Analysis shortlist · 12 Sep 2026.').replace('🤗 HUGGING FACE','AA INDEX v4.3')
s=s.replace('<div id="model-list"','<label class="input-label" for="model-search">FIND A MODEL <span id="model-count">14 MODELS</span></label><input id="model-search" type="search" placeholder="Search models…" autocomplete="off"><div id="model-list"')
s=s.replace('Text generation · Open weights · No gated model access required','Scores and evaluation settings from your supplied chart. K2 Horizon is an estimate, with independent evaluation forthcoming. HF repositories, licences and GPU sizing are not yet verified. All 14 models are mock-only.')
s=s.replace('<strong>1 × NVIDIA L4</strong>','<strong id="summary-gpu">Sizing not verified</strong>').replace('<code>ml.g6.2xlarge</code>','<code id="summary-instance">Not provisioned</code>').replace('id="summary-model">Qwen3 0.6B','id="summary-model">GLM-5.3')
p.write_text(s)
p=root/'app/static/app.js';s=p.read_text();start=s.index(" $('model-list').innerHTML=");end=s.index(" $('provider-list').innerHTML",start)
s=s[:start]+''' const query=$('model-search').value.trim().toLowerCase();
 const models=catalog.models.filter(m=>(m.name+' '+(m.evaluation_setting||'')).toLowerCase().includes(query));
 $('model-count').textContent=`${models.length} / ${catalog.models.length} MODELS`;
 $('model-list').innerHTML=models.map(m=>`<button class="model-card" role="radio" aria-checked="${m.id===selectedModel}" data-model="${esc(m.id)}"><span class="model-icon">${m.chart_order?String(m.chart_order).padStart(2,'0'):'✦'}</span><span class="model-copy"><span class="model-top"><span class="model-name">${esc(m.name)}</span>${m.estimated?'<span class="recommended estimate">ESTIMATE</span>':''}</span><span class="model-id">${m.evaluation_setting?`Evaluated at ${esc(m.evaluation_setting)} · `:''}${m.score!==undefined?'Mock only · HF repository unverified':esc(m.id)}</span></span>${m.score!==undefined?`<span class="index-score"><strong>${m.score}</strong><small>AA INDEX</small></span>`:''}<span class="radio"></span></button>`).join('');
 if(!models.length)$('model-list').innerHTML='<p class="field-note">No matching models. Try another name.</p>';
 for(const b of document.querySelectorAll('[data-model]')){b.disabled=Boolean(current)||creating;b.addEventListener('click',()=>{selectedModel=b.dataset.model;requestId=null;renderCatalog();});}
 const chosen=catalog.models.find(m=>m.id===selectedModel);
 $('summary-model').textContent=chosen?chosen.name:selectedModel;
 $('summary-gpu').textContent=selectedModel.startsWith('mock/')?'Sizing not verified':'1 × NVIDIA L4';
 $('summary-instance').textContent=selectedModel.startsWith('mock/')?'Not provisioned':'ml.g6.2xlarge';
''' +s[end:]
s=s.replace("$('endpoint-name').addEventListener", "$('model-search').addEventListener('input',renderCatalog);\n$('endpoint-name').addEventListener")
p.write_text(s)
p=root/'app/static/style.css';s=p.read_text()+'''\n#model-search{margin-bottom:12px;background:#fff}#model-count{float:right;color:#9aa28f}.model-list{max-height:420px;overflow-y:auto;padding:2px 5px 2px 2px;scrollbar-width:thin;scrollbar-color:#c7d1c0 transparent}.model-card{padding:14px;align-items:center;gap:11px}.model-id{margin-bottom:0;font-size:9px;line-height:1.7}.model-icon{width:28px;height:28px;min-width:28px;font:10px ui-monospace,monospace;background:#eef1e8;color:#7a8c6f;border:0}.index-score{margin-left:auto;text-align:center;min-width:40px}.index-score strong{font-size:22px;font-weight:500;display:block;color:#52704e}.index-score small{font-size:6px;letter-spacing:.5px;color:#89967e}.model-card .radio{margin-top:0}.estimate{background:repeating-linear-gradient(135deg,#eee7d4,#eee7d4 3px,#f7f1e5 3px,#f7f1e5 6px);color:#8f7845}.model-top{flex-wrap:wrap;gap:5px}@media(max-width:650px){.model-name{font-size:12px}.model-list{max-height:370px}.index-score strong{font-size:20px}}\n''';p.write_text(s)
p=root/'README.md';s=p.read_text().replace('Working UI; two allowlisted, pinned Hugging Face models','Working UI; 14 mock-only models from the supplied Artificial Analysis chart, searchable and in chart order')
s=s.replace('Models checked against the Hugging Face Hub on 13 September 2026:', '''## Supplied model shortlist

The picker follows the supplied **Artificial Analysis Intelligence Index v4.3 — Open Source Models** chart, dated **12 September 2026 by its filename**. Scores below are the displayed integers; they are not a live leaderboard fetch or unrounded measurements. Evaluation settings describe the chart run, not a deployed runtime setting.

| Model | Evaluation setting | Displayed score |
| --- | --- | --- |
'''+''.join(f'| {name} | {setting or "Not specified"} | {score}'+(' (estimate)' if slug.startswith('k2-horizon') else '')+' |\n' for slug,name,setting,score in rows)+'''
K2 Horizon's independent evaluation is forthcoming according to the chart legend. All 14 entries are **mock-only**. Their `mock/` identifiers are local catalog keys, not Hugging Face repository names. Repository, licence, revision, runtime compatibility and GPU sizing require verification. The UI does not apply the previous one-L4 configuration to these models. The API rejects their use in live mode before making provider calls.

The two earlier Qwen models are retained only as AWS adapter connection candidates and for old endpoint compatibility; they are not in the new mock picker. They were checked against the Hugging Face Hub on 13 September 2026:
''')
p.write_text(s)
