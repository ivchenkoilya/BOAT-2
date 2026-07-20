/* Reality 106 follow-up: preserve the equipment choice and explain the new interaction button. */
const v106MissionObjective=updateObjective;
let v106EquipmentOffered=false;
updateObjective=function(dt,now){
 const before=state.story?.phase;
 v106MissionObjective(dt,now);
 if(before===0&&state.story?.phase===1&&!v106EquipmentOffered){v106EquipmentOffered=true;showUpgrades(0)}
};
const v106MissionStart=startGame;
startGame=function(demo=false){
 v106MissionStart(demo);
 setTimeout(()=>setCaption('Ищи жёлтый маркер. Рядом появится кнопка ДЕЙСТВИЕ — удерживай её.',5),220);
};
