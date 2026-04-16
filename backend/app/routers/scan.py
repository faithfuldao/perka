from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_staff
from app.database import get_db
from app.models.pass_ import Pass
from app.models.staff import Staff
from app.schemas.location import LocationRead
from app.schemas.pass_ import PassRead

router = APIRouter()


@router.get("/{serial_number}", response_class=HTMLResponse, include_in_schema=False)
async def scan_page(serial_number: str) -> HTMLResponse:
    return HTMLResponse(content=_build_html(serial_number))


@router.get("/{serial_number}/data", summary="Load pass + staff locations for the scan page")
async def scan_data(
    serial_number: str,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
) -> dict[str, Any]:
    result = await db.execute(select(Pass).where(Pass.serial_number == serial_number))
    loyalty_pass = result.scalar_one_or_none()
    if loyalty_pass is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pass not found.")
    if loyalty_pass.brand_id != current_staff.brand_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Pass does not belong to your brand.",
        )

    staff_result = await db.execute(
        select(Staff).where(Staff.id == current_staff.id).options(selectinload(Staff.locations))
    )
    staff_with_locs = staff_result.scalar_one()

    return {
        "loyalty_pass": PassRead.model_validate(loyalty_pass).model_dump(mode="json"),
        "locations": [
            LocationRead.model_validate(loc).model_dump(mode="json")
            for loc in staff_with_locs.locations
        ],
    }


# ── HTML page ─────────────────────────────────────────────────────────────────

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0" />
  <title>Perka — Staff Scan</title>
  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    body{
      font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
      background:#faf8f5;min-height:100vh;
      display:flex;flex-direction:column;align-items:center;justify-content:center;
      padding:1.5rem;color:#3b2410;
    }
    .card{width:100%;max-width:400px;background:white;border-radius:1.25rem;
      box-shadow:0 4px 24px rgba(0,0,0,.08);padding:2rem 1.75rem;}
    .logo{text-align:center;margin-bottom:1.5rem;}
    .logo-dot{width:48px;height:48px;background:#6f4e37;border-radius:50%;
      margin:0 auto .5rem;display:flex;align-items:center;justify-content:center;}
    .logo h1{font-size:1.25rem;font-weight:700;color:#3b2410;}
    .logo p{font-size:.8rem;color:#9e8a7e;margin-top:.2rem;}
    label{display:block;font-size:.85rem;font-weight:600;margin-bottom:.4rem;color:#3b2410;}
    input,select{
      width:100%;padding:.75rem 1rem;border:1.5px solid #d4c4b5;border-radius:.75rem;
      font-size:1rem;color:#1a1009;background:#faf8f5;margin-bottom:1rem;
      outline:none;transition:border-color .15s;appearance:none;
    }
    input:focus,select:focus{border-color:#6f4e37;background:white;}
    .btn{width:100%;padding:.875rem;border:none;border-radius:.75rem;
      font-size:1rem;font-weight:700;cursor:pointer;transition:background .15s,opacity .15s;}
    .btn-primary{background:#6f4e37;color:white;}
    .btn-primary:hover{background:#5a3e2b;}
    .btn-primary:disabled{opacity:.55;cursor:not-allowed;}
    .btn-award{background:#16a34a;color:white;margin-top:.5rem;}
    .btn-award:hover{background:#15803d;}
    .btn-award:disabled{opacity:.55;cursor:not-allowed;}
    .btn-ghost{background:none;color:#9e8a7e;font-size:.8rem;
      padding:.5rem;margin-top:.75rem;width:auto;font-weight:500;border:none;cursor:pointer;}
    .btn-ghost:hover{color:#6f4e37;}
    .points-box{
      text-align:center;
      background:linear-gradient(135deg,#6f4e37,#3b2410);
      border-radius:1rem;padding:1.5rem;color:white;margin-bottom:1.5rem;
    }
    .pts{font-size:3.5rem;font-weight:800;line-height:1;}
    .pts-label{font-size:.75rem;opacity:.7;text-transform:uppercase;letter-spacing:.08em;margin-top:.3rem;}
    .divider{border:none;border-top:1px solid #e8ddd4;margin:1.25rem 0;}
    .hidden{display:none!important;}
    #toast{
      position:fixed;bottom:2rem;left:50%;transform:translateX(-50%);
      padding:.7rem 1.4rem;border-radius:2rem;font-size:.875rem;font-weight:600;
      white-space:nowrap;pointer-events:none;transition:opacity .3s;opacity:0;
    }
    #toast.show{opacity:1;}
    .toast-err{background:#fef2f2;color:#dc2626;border:1px solid #fca5a5;}
    .toast-ok{background:#f0fdf4;color:#16a34a;border:1px solid #86efac;}
    #overlay{
      position:fixed;inset:0;background:rgba(0,0,0,.5);
      display:flex;align-items:center;justify-content:center;padding:1.5rem;z-index:100;
    }
    .success-card{
      background:white;border-radius:1.25rem;padding:2.5rem 2rem;
      text-align:center;width:100%;max-width:320px;
    }
    .check{
      width:64px;height:64px;background:#dcfce7;border-radius:50%;
      margin:0 auto 1.25rem;display:flex;align-items:center;justify-content:center;
    }
    .success-card h2{font-size:1.4rem;font-weight:800;color:#166534;margin-bottom:.5rem;}
    .success-card p{color:#4b7c56;margin-bottom:1.5rem;font-size:.95rem;line-height:1.5;}
    .btn-done{
      background:#6f4e37;color:white;border:none;border-radius:.75rem;
      padding:.75rem 2rem;font-size:1rem;font-weight:700;cursor:pointer;
    }
    .btn-done:hover{background:#5a3e2b;}
  </style>
</head>
<body>

<!-- LOGIN -->
<div id="login-view" class="card hidden">
  <div class="logo">
    <div class="logo-dot">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
        <path d="M6 8h12v2a6 6 0 01-12 0V8z" fill="white"/>
        <path d="M16 8c0-1.1-.9-2-2-2h-4a2 2 0 00-2 2" stroke="white" stroke-width="1.5" stroke-linecap="round"/>
      </svg>
    </div>
    <h1>Perka Staff</h1>
    <p>Sign in to award stamps</p>
  </div>
  <label for="inp-email">Email</label>
  <input id="inp-email" type="email" autocomplete="email" placeholder="barista@shop.com" />
  <label for="inp-pw">Password</label>
  <input id="inp-pw" type="password" autocomplete="current-password" placeholder="••••••••" />
  <button class="btn btn-primary" id="login-btn" onclick="doLogin()">Sign in</button>
</div>

<!-- SCAN -->
<div id="scan-view" class="card hidden">
  <div class="logo">
    <div class="logo-dot">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
        <path d="M6 8h12v2a6 6 0 01-12 0V8z" fill="white"/>
        <path d="M16 8c0-1.1-.9-2-2-2h-4a2 2 0 00-2 2" stroke="white" stroke-width="1.5" stroke-linecap="round"/>
      </svg>
    </div>
    <h1>Perka Staff</h1>
    <p>Award loyalty stamps</p>
  </div>

  <div class="points-box">
    <div class="pts" id="pts-val">—</div>
    <div class="pts-label">Current stamps</div>
  </div>

  <div id="loc-wrap" class="hidden">
    <label for="loc-sel">Your location</label>
    <select id="loc-sel"></select>
    <hr class="divider" />
  </div>

  <button class="btn btn-award" id="award-btn" onclick="doAward()">+ Award stamp</button>
  <div style="text-align:center">
    <button class="btn-ghost" onclick="doLogout()">Sign out</button>
  </div>
</div>

<!-- SUCCESS OVERLAY -->
<div id="overlay" class="hidden">
  <div class="success-card">
    <div class="check">
      <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
        <path d="M7 16l6 6 12-12" stroke="#16a34a" stroke-width="3"
              stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </div>
    <h2>Stamp awarded!</h2>
    <p id="ok-msg"></p>
    <button class="btn-done" onclick="closeOverlay()">Done</button>
  </div>
</div>

<!-- TOAST -->
<div id="toast"></div>

<script>
const SERIAL = "SERIAL_PLACEHOLDER";
const TK = "perka_token";
let locs = [], pass = null;

const $ = id => document.getElementById(id);
const show = id => $(id).classList.remove("hidden");
const hide = id => $(id).classList.add("hidden");

function toast(msg, ok) {
  const el = $("toast");
  el.textContent = msg;
  el.className = (ok ? "toast-ok" : "toast-err") + " show";
  clearTimeout(el._t);
  el._t = setTimeout(() => el.classList.remove("show"), 3000);
}

async function doLogin() {
  const email = $("inp-email").value.trim();
  const pw = $("inp-pw").value;
  if (!email || !pw) { toast("Enter email and password"); return; }
  const btn = $("login-btn");
  btn.disabled = true; btn.textContent = "Signing in…";
  try {
    const r = await fetch("/auth/staff/login", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({email, password: pw}),
    });
    if (!r.ok) { const d = await r.json(); throw new Error(d.detail || "Login failed"); }
    const d = await r.json();
    localStorage.setItem(TK, d.access_token);
    await loadScan();
  } catch(e) { toast(e.message); }
  finally { btn.disabled = false; btn.textContent = "Sign in"; }
}

async function loadScan() {
  hide("login-view");
  const token = localStorage.getItem(TK);
  try {
    const r = await fetch("/scan/" + SERIAL + "/data", {
      headers: {"Authorization": "Bearer " + token},
    });
    if (r.status === 401 || r.status === 403) { doLogout(); return; }
    if (!r.ok) { const d = await r.json(); throw new Error(d.detail || "Could not load pass"); }
    const d = await r.json();
    pass = d.loyalty_pass;
    locs = d.locations;

    $("pts-val").textContent = pass.points;

    const sel = $("loc-sel");
    sel.innerHTML = "";
    if (locs.length > 1) {
      locs.forEach(l => {
        const o = document.createElement("option");
        o.value = l.id;
        o.textContent = l.name + (l.address ? " — " + l.address : "");
        sel.appendChild(o);
      });
      show("loc-wrap");
    } else if (locs.length === 0) {
      toast("No locations assigned to your account. Contact your admin.");
      show("login-view"); return;
    }
    show("scan-view");
  } catch(e) { toast(e.message); show("login-view"); }
}

async function doAward() {
  const locationId = locs.length === 1 ? locs[0].id : $("loc-sel").value;
  if (!locationId) { toast("Select a location"); return; }
  const btn = $("award-btn");
  btn.disabled = true; btn.textContent = "Awarding…";
  try {
    const r = await fetch("/passes/" + SERIAL + "/award", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + localStorage.getItem(TK),
      },
      body: JSON.stringify({location_id: locationId}),
    });
    if (r.status === 401 || r.status === 403) { doLogout(); return; }
    if (!r.ok) { const d = await r.json(); throw new Error(d.detail || "Failed to award stamp"); }
    const d = await r.json();
    $("pts-val").textContent = d.total_points;
    $("ok-msg").textContent = "+" + d.points_awarded + " stamp added. Total: "
      + d.total_points + " stamps." + (d.reward_earned ? " Reward unlocked!" : "");
    show("overlay");
  } catch(e) { toast(e.message); }
  finally { btn.disabled = false; btn.textContent = "+ Award stamp"; }
}

function closeOverlay() { hide("overlay"); }

function doLogout() {
  localStorage.removeItem(TK);
  hide("scan-view"); hide("overlay");
  show("login-view");
}

document.addEventListener("DOMContentLoaded", () => {
  $("inp-pw").addEventListener("keydown", e => { if (e.key === "Enter") doLogin(); });
  const token = localStorage.getItem(TK);
  if (token) { loadScan(); } else { show("login-view"); }
});
</script>
</body>
</html>"""


def _build_html(serial: str) -> str:
    return _HTML_TEMPLATE.replace("SERIAL_PLACEHOLDER", serial)
