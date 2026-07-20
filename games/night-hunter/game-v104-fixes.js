/* Reality 104 follow-up: visible generator switches and one weapon choice after restoring the security terminal. */
const v104FixBaseObjective=updateObjective,v104FixBaseDrawObjectives=drawObjectives;
let v104WeaponChoiceShown=false;
updateObjective=function(dt,now){const before=state.story?.phase;v104FixBaseObjective(dt,now);if(before===0&&state.story?.phase===1&&!v104WeaponChoiceShown){v104WeaponChoiceShown=true;showUpgrades(0)}};
drawObjectives=function(now){v104FixBaseDrawObjectives(now);const s=state.story;if(s?.phase!==1)return;for(const b of state.breakers){ctx.save();ctx.shadowColor=b.active?'#75ffe5':'#ffca68';ctx.shadowBlur=10;ctx.fillStyle=b.active?'#174d46':'#3d2914';ctx.strokeStyle=b.active?'#cafff5':'#ffca68';ctx.lineWidth=3;ctx.fillRect(b.x-17,b.y-24,34,48);ctx.strokeRect(b.x-17,b.y-24,34,48);ctx.shadowBlur=0;if(!b.active&&b.progress>0)v104Progress(b,b.progress/1.15);ctx.restore()}};
