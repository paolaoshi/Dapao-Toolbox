import { app } from "../../scripts/app.js";

const choices = [
  ["采用脸图完整发型", "发型", [[false,"保留底图"],[true,"采用脸图发型"]]],
  ["眼镜", "眼镜", [["保留底图","保留底图"],["跟随脸图","跟随脸图"],["去掉眼镜","去掉"]]],
  ["口罩", "口罩", [["保留底图","保留底图"],["跟随脸图","跟随脸图"],["去掉口罩","去掉口罩"]]],
  ...["帽子","头饰","耳饰","颈饰"].map(name=>[name,name,[["保留底图","保留底图"],["跟随脸图","跟随脸图"],["去掉","去掉"]]]),
  ["脸型", "脸型", [["自然适配","自然适配"],["保留底图轮廓","保留底图"],["跟随脸图轮廓","跟随脸图"]]],
  ["朝向", "朝向", [["跟随底图","跟随底图"],["跟随脸图","跟随脸图"]]],
];
const ranges = [
  ["脸型参考强度","脸型参考强度",0,100,1],
  ["五官相似度","脸图五官强度",0,100,1],
  ["脸图表情强度","表情混合比例",0,100,1],
  ["旧发丝清理","旧发丝清理",0,100,1],
  ["取景外扩","取景外扩",0.1,1.5,0.05],
  ["边缘柔和度","边缘柔和度",0.005,0.12,0.005],
];

function attach(node) {
  if (node.widgets?.some(w => w.name === "换脸控制面板")) return;
  const widgets = new Map(node.widgets.map(w => [w.name,w]));
  if (![...choices,...ranges].every(([name]) => widgets.has(name))) return;
  const el = document.createElement("div");
  el.className = "dapao-face-controls";
  const sync = [];
  const tabs=document.createElement("div");tabs.className="dapao-face-tabs";el.append(tabs);
  let section="常用设置",active=section;const sections=[];
  function tabRefresh(){for(const [key,label,group] of sections){label.style.display=group.style.display=key===active?"":"none";} for(const b of tabs.children)b.setAttribute("aria-pressed",String(b.textContent===active));}
  for(const key of ["常用设置","肤色与细节"]){const b=document.createElement("button");b.type="button";b.textContent=key;b.onclick=()=>{active=key;tabRefresh()};tabs.append(b);}
  function row(title) {
    const label = document.createElement("span");
    label.textContent = title;
    const group = document.createElement("div");
    group.setAttribute("role","group");
    group.setAttribute("aria-label",title);
    el.append(label, group);sections.push([section,label,group]);
    return group;
  }
  function set(w,value) {
    w.value = value;
    w.callback?.call(w,value,app.canvas,node);
    node.graph?.change();
    node.setDirtyCanvas(true,true);
    refresh();
  }
  function refresh() { for (const fn of sync) fn(); }
  function hide(w) {
    w.hidden = true;
    w.computeSize = () => [0,-4];
  }
  for (const [name,title,options] of choices) {
    const w=widgets.get(name), group=row(title);
    hide(w);
    for (const [value,label] of options) {
      const button=document.createElement("button");
      button.type="button";
      group.append(button);
      button.onclick=() => set(w,value);
      sync.push(() => {
        const selected=w.value===value;
        button.textContent=(selected ? "✓ " : "")+label;
        button.setAttribute("aria-pressed",String(selected));
      });
    }
  }
  for (const [name,title,min,max,step] of ranges) {
    const w=widgets.get(name), group=row(title), isStrength=name==="五官相似度";
    if (name==="脸型参考强度") {
      el.querySelector('[role="group"][aria-label="脸型"]').after(group.previousElementSibling,group);
    }
    if (name==="脸图表情强度") {
      const sources=row("表情来源");
      // Insert presets above the ratio and keep the original serialized value.
      const ratioLabel=group.previousElementSibling;
      el.insertBefore(sources.previousElementSibling,ratioLabel);
      el.insertBefore(sources,ratioLabel);
      let lastMix=50;
      for (const [label,preset] of [["用底图",0],["混合",null],["用脸图",100]]) {
        const button=document.createElement("button");
        button.type="button";
        button.onclick=()=>set(w,preset ?? lastMix);
        sources.append(button);
        sync.push(()=>{
          const value=Number(w.value), mixed=value>0 && value<100;
          if (mixed) lastMix=value;
          const active=preset===null ? mixed : value===preset;
          button.textContent=(active?"✓ ":"")+label;
          button.setAttribute("aria-pressed",String(active));
        });
      }
    }
    hide(w);
    const input=document.createElement("input"), output=document.createElement("output");
    input.type="range"; input.min=min;input.max=max;input.step=step;
    input.setAttribute("aria-label",title);
    input.oninput=() => {
      const n=input.valueAsNumber;
      set(w,isStrength ? (n===0 ? "标准" : n===100 ? "优先参考脸" : String(n)) : n);
    };
    sync.push(() => {
      const n=w.value==="标准" ? 0 : w.value==="优先参考脸" ? 100 : Number(w.value);
      input.value=n;
      if(name==="脸型参考强度") {
        input.disabled=widgets.get("脸型").value!=="跟随脸图轮廓";
        output.textContent=input.disabled ? "随模式" : n+"/100";
        input.title="跟随脸图时，数值越高，生图模型得到的脸型近景越清晰。0 采用底图轮廓。";
      } else if(name==="脸图表情强度") { output.textContent="底图 "+(100-n)+" / 脸图 "+n;input.setAttribute("aria-valuetext",output.textContent); }
      else output.textContent=(isStrength || name==="旧发丝清理") ? n+"/100" : n.toFixed(name==="取景外扩" ? 2 : 3);
    });
    group.append(input,output);
  }
  section="肤色与细节";
  const detailRows=[["肤色基调",["贴合底图","自然折中","保留脸图"]],["发丝边缘",["忠于脸图","收至耳后"]],...["胡须","妆容彩绘","面部饰件"].map(n=>[n,["自然适配","保留底图","跟随脸图","去掉"]])];
  for(const [key,options] of detailRows){const w=widgets.get(key);if(!w)continue;
    hide(w);const group=row(key);
    for(const value of options){const b=document.createElement("button");b.type="button";b.onclick=()=>set(w,value);group.append(b);
      sync.push(()=>{const sel=w.value===value;b.setAttribute("aria-pressed",String(sel));b.textContent=(sel?"✓ ":"")+value;b.disabled=key==="发丝边缘"&&!widgets.get("采用脸图完整发型").value;});}
  }
  const tip=row("使用提示");tip.textContent="肤色与现场光分别控制。发丝边缘仅在采用脸图发型时生效。面部饰件指鼻环、眉钉、唇钉和面贴；眼镜、口罩与耳饰仍分别控制。";tabRefresh();
  for (const event of ["pointerdown","keydown","keyup"]) el.addEventListener(event,e=>e.stopPropagation());
  const panel=node.addDOMWidget("换脸控制面板","custom",el,{serialize:false,getMinHeight:()=>496,getMaxHeight:()=>496});
  panel.serialize=false;
  refresh();
  const previous=node.onConfigure;
  node.onConfigure=function(...args) {const result=previous?.apply(this,args);refresh();return result;};
  requestAnimationFrame(refresh);
}

const css=document.createElement("style");
css.textContent=`
.dapao-face-controls{box-sizing:border-box;width:100%;padding:6px 9px;display:grid;grid-template-columns:max-content minmax(0,1fr);align-items:center;gap:4px 8px;background:#19232b;border-radius:8px;color:#e5eded;font:12px/1.2 system-ui,sans-serif}
.dapao-face-tabs{grid-column:1/-1}.dapao-face-controls button:disabled{opacity:.5;cursor:default}.dapao-face-controls>div{display:flex;gap:4px;align-items:center;min-width:0}
.dapao-face-controls button{cursor:pointer;flex:1;min-height:24px;border:1px solid #576675;border-radius:5px;color:#d9e2e8;background:#28343e;font:inherit;white-space:nowrap}
.dapao-face-controls button[aria-pressed=true]{color:#06251f;background:#82e3cd;border-color:#a3ffeb;font-weight:700}
.dapao-face-controls input{flex:1;min-width:30px;accent-color:#82e3cd}
.dapao-face-controls output{min-width:50px;text-align:right;font-variant-numeric:tabular-nums}
`;
document.head.append(css);
app.registerExtension({name:"Dapao.FaceRegionControls",nodeCreated(node) {
  if(node.comfyClass==="DapaoFaceSwapRegion") attach(node);
}});
