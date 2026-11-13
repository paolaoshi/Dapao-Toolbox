import {upgradeOutfitWorkflow,upgradeReferenceScope} from "./outfit_upgrade.mjs";
import {outfitCatalog} from "./outfit_catalog.js";
import {api} from "../../scripts/api.js";
import {app} from "../../scripts/app.js";

const style=document.createElement("style");
style.textContent=`
.dapao-outfit{box-sizing:border-box;width:100%;height:100%;padding:12px;background:#19232b;color:#e3ebef;border-radius:8px;font:14px/1.35 system-ui,sans-serif;overflow:auto;scrollbar-width:thin;display:flex;flex-direction:column;gap:8px}
.dapao-outfit *{box-sizing:border-box}
.dapao-outfit .tabs,.dapao-outfit .group{display:flex;gap:5px;align-items:center;min-width:0;flex:1}
.dapao-outfit .tabs{flex:0;flex-wrap:wrap}.dapao-outfit .tabs button{flex:1 0 58px}
.dapao-outfit .r{display:flex;align-items:center;gap:7px}
.dapao-outfit .r>span{width:80px;flex:none;color:#c9d6dd}
.dapao-outfit button{flex:1;min-width:0;min-height:29px;margin:0;padding:3px 5px;border:1px solid #576675;background:#293640;color:#e1e9ed;border-radius:5px;cursor:pointer;font:inherit;white-space:nowrap}
.dapao-outfit button[aria-pressed=true]{background:#82e3cd;color:#06251f;border-color:#b0ffee;font-weight:700}
.dapao-outfit button:hover:not([aria-pressed=true]):not(:disabled){background:#354650}
.dapao-outfit button:focus-visible,.dapao-outfit input:focus-visible,.dapao-outfit textarea:focus-visible{outline:2px solid #bcfff1}
.dapao-outfit button:disabled,.dapao-outfit input:disabled{opacity:.45;cursor:default}
.dapao-outfit .section{border-top:1px solid #384951;padding-top:7px;display:flex;flex-direction:column;gap:5px}
.dapao-outfit .section>b{font-size:12px;color:#8edfcf;letter-spacing:.04em}
.dapao-outfit .field{width:100%;padding:5px 8px;color:#ebf2f5;background:#111c24;border:1px solid #495e68;border-radius:5px;font:inherit}
.dapao-outfit textarea{resize:none;height:42px}
.dapao-outfit input[type=range]{flex:1;min-width:40px;accent-color:#82e3cd}
.dapao-outfit output{min-width:56px;text-align:right;font-variant-numeric:tabular-nums}
.dapao-outfit .hint{color:#b0c0c8;font-size:12px;margin:0}
.dapao-outfit .decision summary{cursor:pointer;color:#a9dcd6;width:fit-content}
.dapao-outfit .decision pre{margin:5px 0 0;height:104px;overflow:auto;white-space:pre-wrap;overflow-wrap:anywhere;user-select:text;font:inherit}
.dapao-outfit [hidden]{display:none!important}
`;
document.head.append(style);
const instances=new WeakMap();
// The detail upload and its resize node form one optional branch. Mirror the
// source before export too: users can bypass an upload directly on the canvas.
function syncDetailResizers(graph){
 for(const node of graph?._nodes??[]){
   const id=node.properties?.dapaoSizeSource;
   if(id==null || node.type!=="图像缩放V2_孤海")continue;
   const mode=graph.getNodeById(id)?.mode===0?0:2;
   if(node.mode!==mode)node.mode=mode;
 }
}
const types={review:"PrimitiveBoolean",upscale:"PrimitiveBoolean",upscaleEdge:"ImpactInt",outfitPrecision:"TextEncodeQwenImage21",posePrecision:"GoohaiRatioAndResolution",userRequest:"PrimitiveStringMultiline",poseRequest:"PrimitiveStringMultiline",shadowMix:"ImageBlend",outfitLight:"PrimitiveStringMultiline",outfitSkin:"PrimitiveStringMultiline",pose:"PrimitiveBoolean",poseDirect:"PrimitiveBoolean",poseSkeleton:"PrimitiveBoolean",poseCustom:"PrimitiveBoolean",outfitCustom:"PrimitiveBoolean",poseSize:"GoohaiRatioAndResolution",outfitSize:"GoohaiRatioAndResolution",poseLora:"LoraLoaderModelOnly",frameFit:"图像缩放V2_孤海",supplement:"PrimitiveStringMultiline",focus:"PrimitiveBoolean",repair:"PrimitiveStringMultiline",fullPrompt:"PrimitiveStringMultiline",full:"PrimitiveBoolean",wide:"PrimitiveBoolean",second:"DapaoOutfitRules",enabled:"PrimitiveBoolean",ai:"PrimitiveBoolean",inner:"PrimitiveBoolean",hem1:"DapaoHemGuide",hem2:"DapaoHemGuide",region1:"DapaoOutfitRegions",region2:"DapaoOutfitRegions"};
function attach(n){
 const saved=n.properties?.dapaoOutfitPanel; let map=typeof saved==="string"?JSON.parse(saved):saved;
 if(n.type!=="DapaoOutfitRules"||!map||instances.has(n))return;
 if(map.full)map={...outfitCatalog,...map};
 const el=document.createElement("div");el.className="dapao-outfit";el.setAttribute("aria-label","换装可视化设置");
 let stage=1,tab=0,updates=[],lastLayout,categoryPage="服装",accessoryPage="常用";
 // The frontend reserves 20px inside a DOM widget. Size for the visible rows
 // and re-fit legacy saved node heights only on attach / mode changes.
 const isFull=()=>value("full","value")?.value!==false;
 const advanced=()=>map.detailSlots?(n.properties.outfitAdvanced ?? !isFull()):!isFull();
 let showAppearance=false,showDecision=false,showDetails=false,showPose=false,showSizes=false,showReview=false,renderedPoseActive;
 const panelHeight=()=>{
   if(!map.full)return 492;
   const poseExpanded=showPose && (!map.poseProminent || value("pose","value")?.value===true);
   const bodyHeight=!advanced()?104:map.catalog?(categoryPage==="范围设置"?565:categoryPage==="服装"?465:420):154;
   return bodyHeight+(map.review?76:0)+(showReview?120:0)+(map.upscale?108:0)+(map.outfitPrecision?86:0)+(map.userRequest?62:0)+(map.poseRequest?100:0)+(map.ai?40:0)+(map.decisionPreview?30:0)+(showDecision?110:0)
     +(map.outfitLight?32:0)+(showAppearance?120:0)+(map.pose?(map.poseProminent?110:70):0)+(poseExpanded?(map.poseProminent?215:255):0)+(poseExpanded && value("poseCustom","value")?.value?110:0)+(showSizes?170:0)+(map.detailSlots?30:0)+(showDetails?300:0);
 };
 function fit(){if(!map.full || !n.graph)return;
   const mode=panelHeight();if(lastLayout===mode)return;lastLayout=mode;
   n.setSize([Math.max(400,n.size[0]),Math.ceil(n.computeSize()[1])+4]);
   n.setDirtyCanvas(true,true);
 }
 const owner=key=>{if(key==="first")return n;let o=n.graph?.getNodeById(map[key]);return o?.type===types[key]?o:null;};
 const usesSupplement=(k,id)=>map.supplement && k==="first" && id==="补充要求";
 const value=(k,id)=>usesSupplement(k,id)?owner("supplement")?.widgets?.find(w=>w.name==="value"):owner(k)?.widgets?.find(w=>w.name===id);
 const stageKey=()=>stage===1?"first":"second";
 const find=k=>typeof k==="function"?k():k;
 function edit(k,id,v){k=find(k);const o=owner(usesSupplement(k,id)?"supplement":k),w=value(k,id);if(!w||w.value===v)return;
   o.graph?.beforeChange?.();w.value=v;w.callback?.call(w,v,app.canvas,o);if(map.repair && k==="hem1" && id==="版型")applyScope(n.properties.outfitItems || [n.properties.outfitItem || value("first","换装类别")?.value]);o.graph?.afterChange?.();o.graph?.change?.();o.setDirtyCanvas(true,true);refresh();}
 function applyScope(items){
   const focus=value("focus","value");
   if(focus)focus.value=items.length===1 && map.focusItems.includes(items[0]);
   const wide=value("wide","value");if(!wide)return;
   if(!map.repair){wide.value=items.length>1 || map.upperItems.includes(items[0]);return;}
   const scope=n.properties.outfitScope || "自动适配";
   const hem=value("hem1","版型")?.value;
   wide.value=scope==="整图适配" || (scope==="自动适配" && (!hem || hem==="沿用原轮廓") && (items.length>1 || !map.localDetails.includes(items[0])));
 }
 function applyRepairs(active){
   const widget=value("repair","value");if(!widget)return;
   const chosen=n.properties.outfitRepairs || [];
   const rules=Object.assign({},...Object.values(map.repairGroups));
   widget.value=active?chosen.map(k=>rules[k]).filter(Boolean).join("\n"):"";
 }
 function refresh(){syncDetailResizers(n.graph);for(const fn of updates)fn();fit();}
 function child(tag,cls,text,parent){let t=document.createElement(tag);if(cls)t.className=cls;if(text)t.textContent=text;parent.append(t);return t;}
 function group(parent,title){let r=child("div","r",null,parent);child("span","",title,r);let g=child("div","group",null,r);g.setAttribute("role","group");g.setAttribute("aria-label",title);return g;}
 function section(title){let s=child("div","section",null,el);child("b","",title,s);return s;}
 function btn(g,label,on,clicked,enabled=()=>true){let b=child("button","","",g);b.type="button";b.setAttribute("aria-label",label);b.onclick=clicked;updates.push(()=>{let sel=!!on(),txt=(sel?"✓ ":"")+label;if(b.textContent!==txt)b.textContent=txt;b.setAttribute("aria-pressed",String(sel));b.disabled=!enabled();});}
 function choices(g,k,id,pairs){for(let [val,label] of pairs)btn(g,label,()=>value(find(k),id)?.value===val,()=>{edit(k,id,val);if(k==="enabled"&&!val){stage=1;draw();}},()=>!!value(find(k),id));}
 function field(parent,label,k,id,multi=false){let g=group(parent,label),input=child(multi?"textarea":"input","field",null,g);input.setAttribute("aria-label",label);input.placeholder=label==="换装要求"?"只写换装要求，例如只换外套、将上衣改成蓝色；留空使用默认换装":label==="姿势要求"?"只在第二次生效，例如拿手机、坐沙发；未要求时保留原背景与光线":label==="本次要求"?"选填，例如手持银色手机、换成海边背景，或让外套颜色更亮":label==="补充要求"?"选填，例如保留袖口刺绣":"选填，多个英文词用逗号分隔";
 input.oninput=()=>edit(k,id,input.value);updates.push(()=>{let w=value(find(k),id);input.disabled=!w;if(document.activeElement!==input)input.value=w?.value??"";});return g.parentElement;}
 function range(parent,title,k,id,min,max,step,suffix,enabled=()=>true){let g=group(parent,title),i=child("input","",null,g),out=child("output","",null,g);i.type="range";i.min=min;i.max=max;i.step=step;i.setAttribute("aria-label",title);i.oninput=()=>edit(k,id,i.valueAsNumber);
 updates.push(()=>{let w=value(find(k),id);i.disabled=!w||!enabled();if(w){i.value=w.value;out.textContent=w.value+suffix;}});}
 function fold(label,open,changed){
   const box=child("details","decision",null,el),summary=child("summary","",label,box);
   box.open=open;box.ontoggle=()=>{if(box.isConnected){changed(box.open);refresh();}};
   return {summary,body:child("div","section",null,box)};
 }
 function sizeFields(parent,key,custom,follow){
   const toggles=group(parent,"画幅");
   for(const [v,label] of [[false,follow],[true,"自定义画幅"]])
     btn(toggles,label,()=>value(custom,"value")?.value===v,()=>{edit(custom,"value",v);draw();});
   if(!value(custom,"value")?.value)return;
   const field=group(parent,"比例"), select=child("select","field",null,field);
   select.setAttribute("aria-label","输出比例");
   for(const v of ["原始比例","1:1","2:3","3:2","3:4","4:3","5:7","9:16","16:9","21:9","1:2","2:1","自定义宽高"])
     select.add(new Option(v,v));
   select.value=value(key,"比例")?.value || "原始比例";
   select.onchange=()=>{edit(key,"比例",select.value);draw();};
   function number(label,id,min,max){
     const row=group(parent,label),input=child("input","field",null,row);
     input.type="number";input.min=min;input.max=max;input.step=1;input.value=value(key,id)?.value??1024;
     input.setAttribute("aria-label",label);
     input.onchange=()=>{if(!input.checkValidity() || !Number.isInteger(input.valueAsNumber)){input.reportValidity();input.value=value(key,id).value;return;}if(id==="固定边像素")edit(key,"模式","固定长边");edit(key,id,input.valueAsNumber);};
   }
   if(select.value==="自定义宽高"){number("输出宽度","自定宽度",64,2048);number("输出高度","自定高度",64,2048);}
   else {number("输出长边","固定边像素",128,2048);}
   if(key==="outfitSize"){
     choices(group(parent,"人物构图"),"frameFit","缩放模式",[["裁剪","居中裁剪"],["填充_边缘像素","保留全图并补边"]]);
   }
 }
 function drawPose(){
   const active=()=>value("pose","value")?.value===true;
   if(map.poseProminent){
     const toggles=group(el,"姿势参考");
     for(const [v,label] of [[false,"关闭"],[true,"开启"]])
       btn(toggles,label,()=>active()===v,()=>{showPose=v;edit("pose","value",v);draw();},()=>!!value("pose","value"));
     if(!active()){child("p","hint","开启后，按参考动作调整换装成图。已上传的参考图和设置会保留。",el);return;}
   }
   const {body,summary}=fold(map.poseProminent?"姿势参考设置":"姿势参考",showPose,open=>showPose=open);
   const slot=n.graph?.getNodeById(map.poseImage), w=slot?.widgets?.find(v=>v.name==="image");
   const hasFile=()=>!!w?.value && w.value!=="无";
   updates.push(()=>{summary.textContent=(map.poseProminent?"姿势参考设置 · ":"姿势参考 · ")+(active()?(hasFile()?"已加载参考图":"等待上传"):"关闭");});
   if(!map.poseProminent)choices(group(body,"姿势替换"),"pose","value",[[false,"关闭"],[true,"开启"]]);
   const row=group(body,"参考图"), name=child("span","hint",null,row);
   name.style.cssText="flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap";
   const input=child("input","",null,row);input.type="file";input.accept="image/png,image/jpeg,image/webp";input.hidden=true;
   const upload=child("button","","上传姿势参考",row);upload.type="button";upload.onclick=()=>input.click();
   const msg=child("p","hint","",body);msg.setAttribute("role","status");
   updates.push(()=>{name.textContent=hasFile()?String(w.value).split("/").pop():"未上传";name.title=hasFile()?w.value:"";});
   input.onchange=async()=>{
     const file=input.files?.[0];if(!file||!w)return;input.value="";upload.disabled=true;msg.textContent="正在上传…";
     try{
       const data=new FormData();data.append("image",file);data.append("subfolder","dapao_outfit_pose");
       const response=await api.fetchApi("/upload/image",{method:"POST",body:data});if(!response.ok)throw Error("HTTP "+response.status);
       const result=await response.json(),path=[result.subfolder,result.name].filter(Boolean).join("/");
       if(n.graph?.getNodeById(map.poseImage)!==slot)return;
       n.graph.beforeChange?.();if(Array.isArray(w.options?.values)&&!w.options.values.includes(path))w.options.values.push(path);
       w.value=path;w.callback?.call(w,path,app.canvas,slot);n.graph.afterChange?.();n.graph.change?.();refresh();
       msg.textContent=active()?"已加载姿势参考。":"已加载，开启后将在换装完成时改姿势。";
     }catch(e){msg.textContent="姿势参考上传失败："+e.message;}finally{upload.disabled=false;}
   };
   const kind=group(body,"输入类型");
   for(const [v,label] of [[false,"真人照片"],[true,"已有姿势图"]])
     btn(kind,label,()=>value("poseDirect","value")?.value===v,()=>{edit("poseDirect","value",v);draw();});
   if(value("poseDirect","value")?.value)child("p","hint","直接使用上传的深度图、人体线稿或骨架。",body);
   else choices(group(body,"照片提取"),"poseSkeleton","value",[[false,"深度图"],[true,"人体骨架"]]);
   range(body,"姿势 LoRA","poseLora","strength_model",0,1,0.05,"");
   sizeFields(body,"poseSize","poseCustom","跟随换装成图");
 }
 function drawDetailSlots(parent){
   child("p","hint","主图决定款式。特写可选领口袖口、面料纹样或鞋包五金，同一细节请用清晰近照。",parent);
   const focus=group(parent,"参考重点");
   const k=isFull()?"fullPrompt":"first",id=isFull()?"value":"补充要求";
   for(const [label,rule] of [["面料","Match the fabric texture and sheen from the detail views."],["纹样","Match motif scale, embroidery and pattern placement from the detail views."],["工艺","Match seam finishes, closures and edge construction from the detail views."]]){
     btn(focus,label,()=>String(value(k,id)?.value||"").split("\n").includes(rule),()=>{
       const enable=!String(value(k,id)?.value||"").split("\n").includes(rule);
       for(const [ownerKey,fieldName] of [["fullPrompt","value"],["first","补充要求"]]){
         const target=value(ownerKey,fieldName);
         if(!target)continue;
         const lines=String(target.value||"").split("\n").filter(line=>line && line!==rule);
         if(enable)lines.push(rule);
         edit(ownerKey,fieldName,lines.join("\n"));
       }
     });
   }   for(const [index,id] of map.detailSlots.entries()){
     const slot=n.graph.getNodeById(id), w=slot?.widgets?.find(v=>v.name==="image");if(!w)continue;
     const row=group(parent,"细节图 "+(index+1)),thumb=child("img","",null,row);
     thumb.alt="";thumb.style.cssText="width:50px;height:50px;object-fit:contain;background:#111c24";
     const name=child("span","hint",null,row);name.style.cssText="flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap";
     const picker=child("input","",null,row);picker.type="file";picker.accept="image/png,image/jpeg,image/webp";picker.hidden=true;
     const upload=child("button","","上传",row);upload.type="button";upload.setAttribute("aria-label","上传细节图 "+(index+1));upload.onclick=()=>picker.click();
     const toggle=child("button","","",row);toggle.type="button";
     toggle.onclick=()=>{n.graph.beforeChange?.();slot.mode=slot.mode===0?4:0;slot.properties.outfitDetailActive=slot.mode===0;n.graph.afterChange?.();n.graph.change?.();refresh();};
     const message=child("p","hint","",parent);message.setAttribute("role","status");
     picker.onchange=async()=>{
       const file=picker.files?.[0];if(!file)return;picker.value="";upload.disabled=true;message.textContent="正在上传…";
       try{
         const data=new FormData();data.append("image",file);data.append("subfolder","dapao_outfit_details");
         const response=await api.fetchApi("/upload/image",{method:"POST",body:data});if(!response.ok)throw Error("HTTP "+response.status);
         const result=await response.json();if(!n.graph || n.graph.getNodeById(id)!==slot)return;
         const path=[result.subfolder,result.name].filter(Boolean).join("/");
         n.graph.beforeChange?.();if(Array.isArray(w.options?.values)&&!w.options.values.includes(path))w.options.values.push(path);
         w.value=path;w.callback?.call(w,path,app.canvas,slot);slot.properties.outfitDetailPath=path;slot.properties.outfitDetailActive=true;
         slot.mode=0;n.graph.afterChange?.();n.graph.change?.();message.textContent="";refresh();
       }catch(error){message.textContent="上传失败，可重试："+error.message;}finally{upload.disabled=false;}
     };
     updates.push(()=>{
       const active=slot.mode===0,path=String(w.value||"");
       if(active && path)slot.properties.outfitDetailPath=path;
       const known=active || slot.properties.outfitDetailPath===path;
       toggle.disabled=!known;toggle.textContent=active?"停用":"启用";toggle.setAttribute("aria-label",toggle.textContent+"细节图 "+(index+1));
       name.textContent=known?path.split("/").pop():"未上传";name.title=known?path:"";thumb.hidden=!known;
       if(known && thumb.dataset.path!==path){thumb.dataset.path=path;thumb.src=api.apiURL("/view?"+new URLSearchParams({filename:path.split("/").pop(),subfolder:path.split("/").slice(0,-1).join("/"),type:"input"}));}
     });
   }
 } function draw(){updates=[];renderedPoseActive=value("pose","value")?.value===true;el.replaceChildren();
 if(map.full){
   const full=()=>value("full","value")?.value!==false;
   const g=group(el,"换装模式");
      for(const [simple,label] of [[true,"默认完整替换"],[false,"高级换装"]]){
     btn(g,label,()=>simple!==advanced(),()=>{
       if(simple===!advanced())return;
       n.properties.outfitAdvanced=!simple;applyRepairs(!simple);
       const chosen=n.properties.outfitItem || value("first","换装类别")?.value;
       edit("full","value",simple || chosen==="整套服装");
       n.graph.change?.();draw();
     });
   }
   if(map.ai){
     const fallback=map.fullReferenceScope?"仅选区失败时":"关闭";
     choices(group(el,"AI 看图优化"),"ai","value",[[true,"每次开启"],[false,fallback]]);
   }
   if(map.userRequest)field(el,map.poseRequest?"换装要求":"本次要求","userRequest","value",true);
   if(map.poseRequest){
     field(el,"姿势要求","poseRequest","value",true);
     const note=child("p","hint","",el);
     updates.push(()=>{note.textContent=value("pose","value")?.value===true?"换装要求只影响第一次；姿势阶段要求只影响第二次。两项均可留空。":"姿势已关闭：姿势阶段要求保留，但本次不执行。换装要求留空沿用默认换装。";});
   }
   if(map.outfitPrecision && map.posePrecision){
     const row=group(el,"绘制精度");
     const presets=[[768,.7,"快速"],[1024,1,"标准"],[1280,1.6,"精细"],[1536,2.3,"高清"]];
     for(const [resolution,mp,label] of presets){
       btn(row,label,()=>value("outfitPrecision","resolution")?.value===resolution && Math.abs((value("posePrecision","百万像素")?.value??0)-mp)<.00001,
         ()=>{edit("outfitPrecision","resolution",resolution);edit("posePrecision","模式","总像素");edit("posePrecision","百万像素",mp);},
         ()=>!!value("outfitPrecision","resolution") && !!value("posePrecision","百万像素"));
     }
     const note=child("p","hint","",el);
     updates.push(()=>{
       const resolution=value("outfitPrecision","resolution")?.value,mp=value("posePrecision","百万像素")?.value;
       const custom=value("outfitCustom","value")?.value || (value("pose","value")?.value && value("poseCustom","value")?.value);
       const text=custom?"已使用自定义画幅：实际采样宽高以尺寸设置为准；绘制精度仍影响换装参考图。":"同时设置换装与姿势的实际绘制精度，越高越耗时。保存宽高在下方出图尺寸中设置。";
       note.textContent=text+" 换装参数 "+resolution+"，姿势像素预算 "+Number((mp*1048576/1000000).toFixed(2))+" MP。";
     });
   }
   if(map.pose && map.poseProminent)drawPose();
   if(map.upscale && map.upscaleEdge){
     choices(group(el,"超清放大"),"upscale","value",[[false,"关闭"],[true,"开启"]]);
     const row=group(el,"放大长边");
     for(const [edge,label] of [[2048,"2K"],[4096,"4K"],[8192,"8K"]])
       btn(row,label,()=>value("upscaleEdge","value")?.value===edge,()=>edit("upscaleEdge","value",edge),()=>value("upscale","value")?.value===true && !!value("upscaleEdge","value"));
     const note=child("p","hint","",el);
     updates.push(()=>{note.textContent=value("upscale","value")?.value ? "SeedVR2 放大最终成品，长边 "+value("upscaleEdge","value")?.value+" 像素，保持比例。8K 耗时和显存占用更高。" : "默认关闭。开启后处理最终换装或姿势成品，不改变前面的绘制精度。";});
   }
   if(map.outfitLight && map.outfitSkin){
     const {body}=fold("衣料光影与肤色",showAppearance,open=>showAppearance=open);
     for(const [label,key,options] of [["衣料光影","outfitLight",map.lightingChoices],["绑带与镂空","outfitSkin",map.skinChoices]]){
       choices(group(body,label),key,"value",Object.entries(options).map(([name,rule])=>[rule,name]));
     }
     if(map.shadowMix)range(body,"提亮强度","shadowMix","blend_factor",0,1,.05,"",()=>value("outfitLight","value")?.value===map.lightingChoices["提亮暗部"]);
   }
   if(map.detailSlots){
     const details=child("details","decision",null,el);
     const summary=child("summary","","",details);
     const body=child("div","section",null,details);
     details.open=showDetails;
     drawDetailSlots(body);
     details.ontoggle=()=>{if(!details.isConnected)return;showDetails=details.open;refresh();};
     updates.push(()=>{
       const count=map.detailSlots.filter(id=>n.graph?.getNodeById(id)?.mode===0).length;
       const label="服装细节图（选填） · 已启用 "+count+"/"+map.detailSlots.length;
       if(summary.textContent!==label)summary.textContent=label;
     });
   }
   if(map.pose){
     const sizes=fold("换装出图尺寸",showSizes,open=>showSizes=open);sizeFields(sizes.body,"outfitSize","outfitCustom","跟随人物图");if(!map.poseProminent)drawPose();
   }
   if(map.review){
     choices(group(el,"结果检查"),"review","value",[[false,"关闭"],[true,"开启"]]);
     child("p","hint","开启后额外看图检查漏件、衣层、结构和取景；只报告疑点，不自动改图。",el);
     const review=fold("查看成图检查",showReview,open=>showReview=open);
     const result=child("pre","",null,review.body);
     updates.push(()=>{
       if(!showReview)return;
       const raw=app.nodeOutputs?.[String(map.reviewPreview)]?.text;
       let text=(Array.isArray(raw)?raw.join("\n"):raw)||"运行后显示检查结果；关闭时不执行额外看图。";
       try{
         const report=JSON.parse(text.replace(/^```(?:json)?\s*|\s*```$/g,""));
         const state={pass:"AI 暂未标出疑点（不代表验收通过）",suspect:"发现需核对的疑点",unknown:"暂时无法可靠判断"};
         const axis={selection:"选件范围",layers:"衣层",construction:"服装结构",framing:"取景",pose:"姿势",environment:"环境与光影",details:"细节"};
         if(Array.isArray(report.checks))text=[state[report.status]||"检查结果",...report.checks.map(c=>(axis[c.axis]||"对照检查")+"："+(c.evidence||state[c.status]||"待核对")),report.repair?.instruction?"建议核对："+report.repair.instruction:"","此检查可能漏判或误判，不会自动改动图片。"].filter(Boolean).join("\n\n");
       }catch{}
       if(result.textContent!==text)result.textContent=text;
     });
   }
   if(map.decisionPreview){
     const details=child("details","decision",null,el);
     child("summary","","查看上次换装指令",details);
     const result=child("pre","",null,details);
     details.open=showDecision;
     details.ontoggle=()=>{if(!details.isConnected)return;showDecision=details.open;refresh();};
     updates.push(()=>{
       if(!details.open)return;
       const raw=app.nodeOutputs?.[String(map.decisionPreview)]?.text;
       const text=(Array.isArray(raw)?raw.join("\n"):raw)||"运行后，这里会显示换装指令或保留原图的原因。";
       if(result.textContent!==text)result.textContent=text;
     });
   }
   if(map.catalog){
     const body=child("div","section",null,el);
     updates.push(()=>body.hidden=!advanced());
     const current=()=>n.properties.outfitItem || Object.keys(map.catalog).find(key=>{
       const [category,ref]=map.catalog[key];
       return category===value("first","换装类别")?.value && (!ref || ref===value("first","参考取件词")?.value) && key!=="自定义组合";
     }) || value("first","换装类别")?.value;
     const selected=()=>Array.isArray(n.properties.outfitItems) && n.properties.outfitItems.length
       ? n.properties.outfitItems : [current()];
     function toggleItem(item){
       const exclusive=k=>k==="整套服装" || k==="自定义组合";
       const previous=selected();
       let next=[item];
       if(!exclusive(item)){
         next=previous.filter(k=>map.catalog[k] && !exclusive(k));
         if(next.includes(item)){
           if(next.length===1)return;
           next=next.filter(k=>k!==item);
         }else next.push(item);
       }
       const multiple=next.length>1;
       const preset=multiple ? ["自定义组合",next.map(k=>map.terms[k]).join(", "),
         next.map(k=>map.catalog[k][2] || map.terms[k]).join(", ")] : map.catalog[next[0]];
       n.graph.beforeChange?.();
       n.properties.outfitAdvanced=true;
       n.properties.outfitItems=next;
       n.properties.outfitItem=next.join("、");
       value("full","value").value=next[0]==="整套服装";

       ["换装类别","参考取件词","人物原衣词"].forEach((key,i)=>value("first",key).value=preset[i]);
       if(multiple || !["裤子","短裤","下装","连衣裙","裙子","半身长裙"].includes(next[0]))value("hem1","版型").value="沿用原轮廓";
       applyScope(next);
       n.graph.afterChange?.();n.graph.change?.();n.setDirtyCanvas(true,true);
       if(item==="自定义组合")categoryPage="范围设置";
       draw();
     }
     const pages=child("div","tabs",null,body);
     for(const page of [...Object.keys(map.groups),...(map.repair?["常见修复"]:[]),"范围设置"]){
       btn(pages,page,()=>categoryPage===page,()=>{categoryPage=page;draw();});
     }
     const status=child("p","hint","",body);
     updates.push(()=>status.textContent="可跨页多选，至少保留一项。已选："+selected().join("、"));
     if(map.manualScope) child("p","hint","服装图画了遮罩时，以框内单品为准；人物图遮罩限制改动位置。",body);
     if(categoryPage==="常见修复"){
       child("p","hint","按本次图片遇到的问题勾选，可组合使用。",body);
       for(const [title,rules] of Object.entries(map.repairGroups)){
         const row=group(body,title);
         for(const name of Object.keys(rules))btn(row,name,()=>n.properties.outfitRepairs?.includes(name),()=>{
           n.graph.beforeChange?.();
           const list=n.properties.outfitRepairs || [];
           n.properties.outfitRepairs=list.includes(name)?list.filter(k=>k!==name):[...list,name];
           applyRepairs(true);n.graph.afterChange?.();n.graph.change?.();refresh();
         });
       }
       const loader=n.graph.getNodeById(map.outfitLora);
       if(loader?.type==="LoraLoaderModelOnly"){
         const row=group(body,"换装 LoRA");
         const go=child("button","","查看模型与强度",row);
         go.type="button";go.onclick=()=>{app.canvas.centerOnNode(loader);app.canvas.selectNode?.(loader);app.canvas.setDirty(true,true);};
       }
     }else if(categoryPage==="范围设置"){
       if(!full() && map.repair){
         const row=group(body,"编辑范围");
         for(const scope of ["自动适配","局部贴回","整图适配"])btn(row,scope,()=>(n.properties.outfitScope || "自动适配")===scope,()=>{
           n.graph.beforeChange?.();n.properties.outfitScope=scope;applyScope(selected());
           n.graph.afterChange?.();n.graph.change?.();draw();
         });
       }
       if(!full() && value("wide","value")?.value){
         child("p","hint","当前组合会参考整张图来适配衣物轮廓。需要限制编辑范围时，可在人物图上手绘遮罩；下方选区参数用于局部贴回。",body);
       }
       if(!full()){choices(group(body,"下摆版型"),"hem1","版型",[["沿用原轮廓","原轮廓"],["宽腿裤","宽腿裤"],["A字裙摆","A 字裙摆"]]);
       range(body,"下摆放宽","hem1","放宽百分比",0,90,5,"%",()=>value("hem1","版型")?.value!=="沿用原轮廓");
       range(body,"选区外扩","region1","外扩像素",0,160,1," px");
       range(body,"边缘羽化","region1","羽化像素",0,64,1," px");
       range(body,"取景余量","region1","上下文比例",.05,1,.05,"");
       field(body,"参考取件词","first","参考取件词");field(body,"人物原衣词","first","人物原衣词");}
       field(body,"补充要求",full()?"fullPrompt":"first",full()?"value":"补充要求",true);
       child("p","hint","人物图手绘限制改动位置。服装主图手绘优先于类别按钮，框内清晰可辨的衣物和配件一起换。",body);
     }else{
       let rows=map.groups[categoryPage];
       if(categoryPage==="配饰" && map.focus){
         const sub=child("div","tabs",null,body);
         for(const name of Object.keys(map.accessorySections))btn(sub,name,()=>accessoryPage===name,()=>{accessoryPage=name;draw();});
         rows=map.accessorySections[accessoryPage];
       }
       for(const [label,names] of Object.entries(rows)){
         const row=group(body,label);row.style.display="grid";row.style.gridTemplateColumns="repeat(4,minmax(0,1fr))";
         for(const item of names.split(" ")){
           btn(row,item,()=>selected().includes(item),()=>toggleItem(item));
         }
       }
       if(categoryPage==="服装"){
         const layer=group(body,"外套内搭");
         const inner="jacket, coat, undershirt, t-shirt";
         for(const [label,words] of [["保留内搭",""],["一起替换",inner]])btn(layer,label,()=>value("first","人物原衣词").value===words,()=>edit("first","人物原衣词",words));
         updates.push(()=>layer.parentElement.hidden=current()!=="外套");
       }
     }
     const hint=child("p","hint","上传人物图和服装主图，一次换上图中的整套穿搭。",el);updates.push(()=>hint.hidden=advanced());
     refresh();return;
   }   let parts=group(el,"替换部位");choices(parts,"first","换装类别",[["上装","上装"],["下装","下装"]]);updates.push(()=>parts.parentElement.hidden=full());
   const tip=child("p","hint","",el);updates.push(()=>tip.textContent=full()?"上传人物图和服装主图，一次换上图中的整套穿搭。":"只替换选中的部位，另一部位沿用人物原图。");
   refresh();return;
 }
 let mode=group(el,"换装件数");choices(mode,"enabled","value",[[false,"只换一件"],[true,"依次换两件"]]);
 let which=group(el,"正在设置");for(const [j,l] of [[1,"第一件"],[2,"第二件"]])btn(which,l,()=>stage===j,()=>{stage=j;draw();},()=>j===1||value("enabled","value")?.value===true);
 let tabs=child("div","tabs",null,el);for(const [j,l] of [[0,"衣物选择"],[1,"范围与细节"]])btn(tabs,l,()=>tab===j,()=>{tab=j;draw();});
 if(!tab){
 let s=section("选择要替换的衣物");
 for(const [lab,opts] of [["上身",["上装","外套","披肩"]],["下身",["下装","裤子","短裤","裙子"]],["全身",["连衣裙","整套服装","泳装"]],["贴身",["内衣上装","内衣下装","内衣套装"]],["配件与组合",["帽子","鞋子","自定义组合"]]]){
 choices(group(s,lab),stageKey,"换装类别",opts.map(v=>[v,v]));}
 let custom=field(s,"组合取件词",stageKey,"参考取件词");updates.push(()=>custom.hidden=value(stageKey(),"换装类别")?.value!=="自定义组合");
 let opts=section("生成设置");choices(group(opts,"看图优化"),"ai","value",[[true,"开启"],[false,"关闭"]]);
 if(stage===1)choices(group(opts,"可见内搭"),"inner","value",[[false,"保留内搭"],[true,"一起替换"]]);
 field(opts,"补充要求",stageKey,"补充要求",true);
 }else{
 let s=section("下装版型");const hem=()=>stage===1?"hem1":"hem2",region=()=>stage===1?"region1":"region2";
 choices(group(s,"轮廓"),hem,"版型",[["沿用原轮廓","原轮廓"],["宽腿裤","宽腿裤"],["A字裙摆","A 字裙摆"]]);
 range(s,"下摆放宽",hem,"放宽百分比",0,90,5,"%",()=>value(hem(),"版型")?.value!=="沿用原轮廓");
 let a=section("局部编辑范围");range(a,"选区外扩",region,"外扩像素",0,160,1," px");range(a,"边缘羽化",region,"羽化像素",0,64,1," px");range(a,"取景余量",region,"上下文比例",.05,1,.05,"");
 let f=section("自动取件不准时再填写");field(f,"参考取件词",stageKey,"参考取件词");field(f,"人物原衣词",stageKey,"人物原衣词");
 child("p","hint",stage===1?"第一件支持手绘优先；下装可在 #161 查看放宽范围。":"第二件从第一步成图重新选区，细节图和手绘只用于第一件。",el);
 }
 refresh();}
 for(const e of ["pointerdown","pointerup","dblclick","wheel","keydown","keyup"])el.addEventListener(e,ev=>ev.stopPropagation());
 for(const w of n.widgets??[])if(["换装类别","参考取件词","人物原衣词","补充要求"].includes(w.name)){w.hidden=true;w.computeSize=()=>[0,-4];}
 const widget=n.addDOMWidget("换装可视化设置","custom",el,{serialize:false,getMinHeight:panelHeight,getMaxHeight:panelHeight});widget.serialize=false;
 if(map.poseProminent)showPose=value("pose","value")?.value===true;
 instances.set(n,{refresh});draw();
 // Re-read saved values after graph loading and external widget edits, without changing serialized inputs.
 const timer=setInterval(()=>{if(!n.graph)return;if(el.isConnected){if(map.poseProminent && renderedPoseActive!==(value("pose","value")?.value===true)){showPose=value("pose","value")?.value===true;draw();}else if(stage===2&&value("enabled","value")?.value===false){stage=1;draw();}else refresh();}},350);
 const remove=n.onRemoved;n.onRemoved=function(...a){clearInterval(timer);return remove?.apply(this,a);};
}
app.registerExtension({name:"Dapao.OutfitVisualControls",
 setup(){const original=app.graphToPrompt;app.graphToPrompt=function(...args){
   syncDetailResizers(this.graph);return original.apply(this,args);
 };},
 beforeConfigureGraph(graph){upgradeOutfitWorkflow(graph,outfitCatalog);upgradeReferenceScope(graph);},
 beforeRegisterNodeDef(cls, data){if(data.name!=="DapaoOutfitRules")return;
   const prev=cls.prototype.onConfigure;cls.prototype.onConfigure=function(...args){const r=prev?.apply(this,args);requestAnimationFrame(()=>attach(this));return r;};
 },
 loadedGraphNode(n){requestAnimationFrame(()=>attach(n));},
 afterConfigureGraph(){requestAnimationFrame(()=>{for(const n of app.graph?._nodes??[])attach(n);});}
});
