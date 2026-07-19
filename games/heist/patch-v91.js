(()=>{
  "use strict";
  (window.__heistV91Patches||(window.__heistV91Patches=[])).push((source,replaceFunction)=>{
    source=replaceFunction(source,"setupTimingPins","renderLockpick",`  function setupTimingPins(kind,master){
    const reinforced=kind==="pins";
    crack.mode=kind;crack.pinCount=master?5:reinforced?4:3;crack.pinIndex=0;crack.pinPos=rand(.08,.24);crack.pinDir=1;crack.pinSpeed=master?1.34:reinforced?1.19:.98;crack.pinTarget=rand(.28,.72);crack.pinBase=crack.pinTarget;crack.pinTolerance=master?.085:reinforced?.115:.145;crack.pinPhase=rand(0,6);crack.pinMovingZone=reinforced;crack.pinPaused=false;crack.pinInputLocked=false;crack.progress=0;
    $("crackInstruction").textContent=reinforced?"Штифт и зелёная зона двигаются. Нажми в момент, когда белый индикатор находится внутри зелёной зоны.":"Индикатор движется сам. Нажми, когда он окажется внутри зелёной зоны.";
    $("crackGame").innerHTML='<div class="v90PinGame v91PinGame '+(reinforced?'reinforced':'mechanical')+'"><div class="v90PinHead"><b id="v90PinLabel">ШТИФТ 1/'+crack.pinCount+'</b><span>Промах сбрасывает только текущий штифт</span></div><div class="v90PinSteps" id="v90PinSteps">'+Array.from({length:crack.pinCount},(_,i)=>'<i class="'+(i===0?'active':'')+'">'+(i+1)+'</i>').join("")+'</div><div class="v90PinMeter" id="v91PinMeter"><i class="v90PinZone" id="v90PinZone"></i><i class="v90PinNeedle" id="v90PinNeedle"></i></div><div class="v91TimingHint"><span>РАНО</span><b>ТОЧНО</b><span>ПОЗДНО</span></div><button class="v90FixPin" id="v90FixPin" type="button">ЗАФИКСИРОВАТЬ ШТИФТ</button></div>';
    const zone=$("v90PinZone"),button=$("v90FixPin"),game=$("crackGame");
    const positionZone=()=>{zone.style.left=(crack.pinTarget-crack.pinTolerance)*100+"%";zone.style.width=crack.pinTolerance*200+"%";};positionZone();
    const resetInput=()=>{crack.pinPos=crack.pinDir>0?.06:.94;crack.pinPaused=false;crack.pinInputLocked=false;game.classList.remove("v91-hit","v91-miss");button.classList.remove("pressed");};
    const evaluate=event=>{
      event.preventDefault();if(crack.resolving||crack.failed||crack.pinInputLocked)return;
      crack.pinInputLocked=true;crack.pinPaused=true;button.classList.add("pressed");
      requestAnimationFrame(()=>{
        const needle=$("v90PinNeedle"),needleRect=needle?.getBoundingClientRect(),zoneRect=zone?.getBoundingClientRect();
        if(!needleRect||!zoneRect){crack.pinInputLocked=false;crack.pinPaused=false;return;}
        const center=needleRect.left+needleRect.width/2,padding=8,inside=center>=zoneRect.left-padding&&center<=zoneRect.right+padding;
        const movingRight=crack.pinDir>0,tooEarly=movingRight?center<zoneRect.left:center>zoneRect.right;
        if(inside){
          game.classList.add("v91-hit");const steps=$("v90PinSteps").children;steps[crack.pinIndex]?.classList.remove("active");steps[crack.pinIndex]?.classList.add("done");crack.pinIndex++;crack.progress=crack.pinIndex/crack.pinCount;$("crackProgressBar").style.width=crack.progress*100+"%";$("crackMessage").textContent="ТОЧНО! Штифт зафиксирован.";$("crackMessage").className="crackMessage success v91-feedback";tg?.HapticFeedback?.notificationOccurred?.("success");
          if(crack.pinIndex>=crack.pinCount){setTimeout(()=>crackStageSuccess(),230);return;}
          setTimeout(()=>{steps[crack.pinIndex]?.classList.add("active");$("v90PinLabel").textContent="ШТИФТ "+(crack.pinIndex+1)+"/"+crack.pinCount;crack.pinSpeed=Math.min(1.68,crack.pinSpeed+.065);crack.pinTarget=rand(.27,.73);crack.pinBase=crack.pinTarget;crack.pinPhase=rand(0,6);positionZone();resetInput();},245);
        }else{
          game.classList.add("v91-miss");crackError(master?8:reinforced?7:5,tooEarly?"СЛИШКОМ РАНО — дождись входа индикатора в зелёную зону.":"СЛИШКОМ ПОЗДНО — нажми до выхода индикатора из зелёной зоны.");
          setTimeout(()=>{if(!crack.failed)resetInput();},310);
        }
      });
    };
    button.addEventListener("pointerdown",evaluate,{passive:false});
  }`);

    source=replaceFunction(source,"renderDial","updateDialTarget",`  function renderDial(master){
    crack.mode="dial";crack.needle=rand(0,360);crack.target=rand(55,305);crack.direction=rng()<.5?-1:1;crack.round=0;crack.rounds=3;crack.window=master?50:60;crack.speed=master?134:110;crack.dialNear=false;crack.dialPaused=false;crack.dialInputLocked=false;crack.progress=0;
    $("crackInstruction").textContent="Стрелка вращается сама. Нажми, когда она окажется внутри зелёного сектора.";
    $("crackGame").innerHTML='<div class="v90DialGame v91DialGame"><div class="v90DialWheel"><i class="v90DialTicks"></i><i class="v90DialZone" id="dialTarget"></i><i class="v90DialNeedle" id="dialNeedle"></i><span class="v90DialHub"></span></div><div class="v90DialInfo"><strong id="dialRound">СЕКТОР 1/3</strong><b id="dialDirection"></b><small>Ничего не вращай пальцем — только нажми в правильный момент.</small><button class="v90DialTap" id="dialTap" type="button">ЗАФИКСИРОВАТЬ</button></div></div>';
    updateDialTarget();const button=$("dialTap");button.addEventListener("pointerdown",event=>{event.preventDefault();if(crack.dialInputLocked||crack.resolving)return;crack.dialInputLocked=true;crack.dialPaused=true;button.classList.add("pressed");requestAnimationFrame(()=>{dialAttempt();setTimeout(()=>{if(!crack.resolving&&!crack.failed){crack.dialInputLocked=false;crack.dialPaused=false;button.classList.remove("pressed");}},220);});},{passive:false});
  }`);

    source=replaceFunction(source,"updateCrack","completeSafe",`  function updateCrack(dt){
    if(!crack.active||crack.failed||crack.resolving)return;if(crack.errorCooldown>0)crack.errorCooldown-=dt;crack.noise=clamp(crack.noise+dt*(crack.safe.tier===4?.92:.5),0,110);updateNoiseUI();if(crack.noise>=100)raiseNoiseAlarm();
    if((crack.mode==="lockpick"||crack.mode==="pins")&&!crack.pinPaused){
      crack.pinPos+=crack.pinDir*dt*crack.pinSpeed;if(crack.pinPos>=.98||crack.pinPos<=.02){crack.pinPos=clamp(crack.pinPos,.02,.98);crack.pinDir*=-1;}
      if(crack.pinMovingZone){crack.pinTarget=clamp(crack.pinBase+Math.sin(performance.now()/850+crack.pinPhase)*.095,.19,.81);const zone=$("v90PinZone");if(zone)zone.style.left=(crack.pinTarget-crack.pinTolerance)*100+"%";}
      const needle=$("v90PinNeedle");if(needle)needle.style.left=crack.pinPos*100+"%";const good=Math.abs(crack.pinPos-crack.pinTarget)<=crack.pinTolerance;$("v90FixPin")?.classList.toggle("ready",good);
    }
    if(crack.mode==="dial"&&!crack.dialPaused){
      crack.needle=(crack.needle+crack.direction*crack.speed*dt+360)%360;const needle=$("dialNeedle");if(needle)needle.style.setProperty("--dial-angle",crack.needle+"deg");const near=degDiff(crack.needle,crack.target)<=crack.window/2+5;$("dialTap")?.classList.toggle("ready",near);if(near&&!crack.dialNear){crack.dialNear=true;tg?.HapticFeedback?.impactOccurred?.("light");}if(!near)crack.dialNear=false;
    }
  }`);

    source=source.replace("Базовая награда ограбления: <b>+${t.base_run_reward}</b><br>За улучшение рекорда: <b>+${t.payable_base}</b>","Сохранённая добыча: <b>+${t.base_run_reward}</b><br>Начислено за забег: <b>+${t.payable_base}</b>");
    return source;
  });
})();
