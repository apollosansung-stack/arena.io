const canvas=document.getElementById("game");
const ctx=canvas.getContext("2d");
const lobby=document.getElementById("lobby");
const gameUI=document.getElementById("gameUI");
const roomsEl=document.getElementById("rooms");
const statusEl=document.getElementById("status");
const nameEl=document.getElementById("name");

let W=innerWidth,H=innerHeight;
function resize(){W=canvas.width=innerWidth;H=canvas.height=innerHeight}
resize(); addEventListener("resize",resize);

const keys={};
addEventListener("keydown",e=>keys[e.key.toLowerCase()]=true);
addEventListener("keyup",e=>keys[e.key.toLowerCase()]=false);

const mouse={x:W/2,y:H/2,down:false};
canvas.addEventListener("mousemove",e=>{mouse.x=e.clientX;mouse.y=e.clientY});
canvas.addEventListener("mousedown",()=>mouse.down=true);
addEventListener("mouseup",()=>mouse.down=false);

let room=null, me=null, running=false, lastSend=0, lastPoll=0, ping=0;
const state={players:{},bullets:[]};

async function api(path,options={}){
  const r=await fetch(path,{cache:"no-store",...options});
  if(!r.ok) throw new Error(await r.text());
  return r.json();
}

async function refreshRooms(){
  try{
    const data=await api("/api/rooms");
    roomsEl.innerHTML="";
    if(!data.rooms.length){roomsEl.innerHTML='<div class="empty">Nenhuma sala. Crie a primeira 😎</div>';return}
    for(const r of data.rooms){
      const el=document.createElement("div");
      el.className="room";
      el.innerHTML=`<div><div class="roomName">${escapeHtml(r.name)}</div><div class="roomMeta">Sala ${r.code}</div></div>
        <div class="roomMeta">👥 ${r.players}/${r.maxPlayers}</div>
        <button class="join">ENTRAR</button>`;
      el.querySelector(".join").onclick=()=>joinRoom(r.code);
      roomsEl.appendChild(el);
    }
  }catch(e){statusEl.textContent="Servidor não encontrado. Rode: py server.py"}
}

function escapeHtml(s){return String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}

async function createRoom(){
  const name=(nameEl.value||"Jogador").trim().slice(0,16);
  try{
    const data=await api("/api/create",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name})});
    await joinRoom(data.code);
  }catch(e){statusEl.textContent=e.message}
}

async function joinRoom(code){
  const name=(nameEl.value||"Jogador").trim().slice(0,16)||"Jogador";
  try{
    const data=await api("/api/join",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({code,name})});
    room=code;me=data.id;running=true;
    lobby.hidden=true;gameUI.hidden=false;
    document.getElementById("roomCode").textContent=room;
    player.x=data.x;player.y=data.y;
    refreshRooms();
    poll();
    pingLoop();
  }catch(e){statusEl.textContent=e.message}
}

async function leaveRoom(){
  if(!room||!me)return;
  try{await api("/api/leave",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({code:room,id:me})})}catch{}
  room=null;me=null;running=false;mouse.down=false;
  lobby.hidden=false;gameUI.hidden=true;refreshRooms();
}

document.getElementById("create").onclick=createRoom;
document.getElementById("refresh").onclick=refreshRooms;
document.getElementById("leave").onclick=leaveRoom;

const player={x:W/2,y:H/2,r:20,speed:4,hp:100,score:0,cool:0};

function move(){
  if(!running)return;
  let dx=0,dy=0;
  if(keys.w||keys.arrowup)dy--;
  if(keys.s||keys.arrowdown)dy++;
  if(keys.a||keys.arrowleft)dx--;
  if(keys.d||keys.arrowright)dx++;
  if(dx||dy){const l=Math.hypot(dx,dy);player.x+=dx/l*player.speed;player.y+=dy/l*player.speed}
  player.x=Math.max(player.r,Math.min(W-player.r,player.x));
  player.y=Math.max(player.r,Math.min(H-player.r,player.y));
  if(player.cool>0)player.cool--;
  if(mouse.down&&player.cool===0){
    const a=Math.atan2(mouse.y-player.y,mouse.x-player.x);
    state.bullets.push({x:player.x+Math.cos(a)*25,y:player.y+Math.sin(a)*25,dx:Math.cos(a),dy:Math.sin(a),owner:me});
    player.cool=9;
  }
}

async function sendState(){
  if(!running||!room||!me)return;
  try{
    await api("/api/update",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({
      code:room,id:me,x:player.x,y:player.y,hp:player.hp,score:player.score
    })});
  }catch{}
}

async function poll(){
  if(!running)return;
  try{
    const data=await api(`/api/state?code=${encodeURIComponent(room)}&id=${encodeURIComponent(me)}`);
    state.players=data.players;
    document.getElementById("online").textContent=Object.keys(data.players).length;
  }catch{}
  setTimeout(poll,100);
}

async function pingLoop(){
  if(!running)return;
  const t=performance.now();
  try{await api("/api/ping");ping=Math.round(performance.now()-t);document.getElementById("ping").textContent=ping}catch{}
  setTimeout(pingLoop,2000);
}

function draw(){
  ctx.clearRect(0,0,W,H);
  for(const [id,p] of Object.entries(state.players)){
    if(id===me)continue;
    ctx.fillStyle="#e74c3c";ctx.beginPath();ctx.arc(p.x,p.y,20,0,Math.PI*2);ctx.fill();
    ctx.fillStyle="#fff";ctx.font="12px Arial";ctx.textAlign="center";ctx.fillText(p.name||"Jogador",p.x,p.y-28);
  }
  for(const b of state.bullets){
    b.x+=b.dx*10;b.y+=b.dy*10;
    ctx.fillStyle="#f1c40f";ctx.beginPath();ctx.arc(b.x,b.y,5,0,Math.PI*2);ctx.fill();
  }
  state.bullets=state.bullets.filter(b=>b.x>-20&&b.x<W+20&&b.y>-20&&b.y<H+20);
  const a=Math.atan2(mouse.y-player.y,mouse.x-player.x);
  ctx.save();ctx.translate(player.x,player.y);ctx.rotate(a);
  ctx.fillStyle="#3498db";ctx.beginPath();ctx.arc(0,0,player.r,0,Math.PI*2);ctx.fill();
  ctx.fillStyle="#222";ctx.fillRect(8,-5,30,10);ctx.restore();
}

function loop(t){
  move();
  if(running&&t-lastSend>80){lastSend=t;sendState()}
  document.getElementById("score").textContent=player.score;
  document.getElementById("hp").textContent=player.hp;
  draw();
  requestAnimationFrame(loop);
}
requestAnimationFrame(loop);
refreshRooms();
setInterval(refreshRooms,3000);
