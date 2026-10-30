// ============================================================
// AutoPilot DC v4 — Object Spy pentru pagini web
// Injectat in fiecare pagina/iframe de Playwright sau Selenium.
//
//  - startSpy('spy')    : contureaza elementul de sub mouse;
//                         click = captureaza obiectul (click-ul NU ajunge la pagina);
//                         Esc = anulare.
//  - startSpy('record') : click-urile si scrierea trec normal in pagina,
//                         dar fiecare actiune e trimisa ca pas de rutina.
//  - startSpy('hover')  : cursorul tinut 3 s pe un element = captureaza (v4.9);
//                         click-urile trec normal (poti deschide meniuri). Esc = stop.
//  - scanStart / scanBatch : scanarea paginii (v4.9) — doar CITESTE pagina,
//                         nu da click si nu trimite nimic la server.
//  - generate(el)       : locatori multipli, ordonati dupa stabilitate.
//  - resolve(kind, val) : gaseste elementele dupa un locator (folosit de Selenium).
//  - highlight(el, ms)  : marcheaza elementul inainte de actiune.
//
// Evenimentele pleaca prin window.__apdcEmit (binding Playwright)
// sau raman in coada window.__apdc.queue (citita de Selenium).
// ============================================================
(function () {
  'use strict';
  if (window.__apdc && window.__apdc.version >= 2) return;
  if (window.__apdc && window.__apdc.stopSpy) { try { window.__apdc.stopSpy(); } catch (e) { /* ignorat */ } }

  var COLOR_SPY = '#00D7A0';     // verde Siemens — marcare in Spy
  var COLOR_REC = '#E05252';     // rosu — inregistrare
  var COLOR_RUN = '#FF9900';     // portocaliu — inainte de actiune la rulare
  var COLOR_HOVER = '#3B82F6';   // albastru — captura cu cursorul tinut 3 s
  var Z = 2147483647;

  // ── 1. Utilitare text ──────────────────────────────────────
  function clean(s) {
    return (s || '').replace(/\s+/g, ' ').trim();
  }
  function short(s, n) {
    s = clean(s);
    return s.length > n ? s.slice(0, n) : s;
  }
  function cssEscape(s) {
    if (window.CSS && CSS.escape) return CSS.escape(s);
    return String(s).replace(/([^\w-])/g, '\\$1');
  }
  function attrQuote(s) {
    return '"' + String(s).replace(/\\/g, '\\\\').replace(/"/g, '\\"') + '"';
  }
  function xpathLiteral(s) {
    s = String(s);
    if (s.indexOf("'") < 0) return "'" + s + "'";
    if (s.indexOf('"') < 0) return '"' + s + '"';
    return "concat('" + s.replace(/'/g, "', \"'\", '") + "')";
  }

  // Id-uri / clase generate automat (React, Angular, Ember, GUID-uri) nu sunt stabile
  function looksGenerated(s) {
    if (!s) return true;
    if (/^[0-9]/.test(s)) return true;
    if (/[0-9a-f]{8}-[0-9a-f]{4}/i.test(s)) return true;          // GUID
    if (/^(ember|ext-gen|ext-comp|gwt-uid|mui-|react-|radix-|headlessui-)\d*/i.test(s)) return true;
    if (/^:r[0-9a-z]+:$/.test(s)) return true;                     // React useId
    if (/\d{4,}/.test(s)) return true;                              // multe cifre la rand
    if (/^[a-z]{1,3}[0-9a-f]{5,}$/i.test(s)) return true;          // hash scurt (ex: c1a2b3f)
    return false;
  }
  function goodClasses(el) {
    var list = [];
    (el.classList ? Array.prototype.slice.call(el.classList) : []).forEach(function (c) {
      if (!looksGenerated(c) && c.length < 40 && !/^(ng-|is-|has-|active|focus|hover|selected|open|show|disabled)/.test(c) && !/__apdc/.test(c)) list.push(c);
    });
    return list.slice(0, 3);
  }

  // ── 2. Rol ARIA si nume accesibil (aproximare a regulilor Playwright) ──
  var INPUT_ROLES = {
    button: 'button', submit: 'button', reset: 'button', image: 'button',
    checkbox: 'checkbox', radio: 'radio', range: 'slider',
    text: 'textbox', email: 'textbox', tel: 'textbox', url: 'textbox', search: 'searchbox',
    number: 'spinbutton', '': 'textbox'
  };

  function roleOf(el) {
    var explicit = el.getAttribute && el.getAttribute('role');
    if (explicit) return explicit.split(' ')[0];
    var tag = el.tagName.toLowerCase();
    switch (tag) {
      case 'button': return 'button';
      case 'a': return el.hasAttribute('href') ? 'link' : null;
      case 'select': return (el.multiple || el.size > 1) ? 'listbox' : 'combobox';
      case 'textarea': return 'textbox';
      case 'option': return 'option';
      case 'img': return el.getAttribute('alt') === '' ? 'presentation' : 'img';
      case 'h1': case 'h2': case 'h3': case 'h4': case 'h5': case 'h6': return 'heading';
      case 'li': return 'listitem';
      case 'table': return 'table';
      case 'tr': return 'row';
      case 'td': return 'cell';
      case 'th': return 'columnheader';
      case 'nav': return 'navigation';
      case 'dialog': return 'dialog';
      case 'input':
        var type = (el.getAttribute('type') || '').toLowerCase();
        if (type === 'hidden' || type === 'password' || type === 'file') return null;
        if (el.hasAttribute('list') && (type === '' || type === 'text')) return 'combobox';
        return INPUT_ROLES.hasOwnProperty(type) ? INPUT_ROLES[type] : null;
    }
    return null;
  }

  function labelText(el) {
    // eticheta <label for=id> sau <label> care contine elementul
    var txt = '';
    if (el.id) {
      try {
        var lab = el.ownerDocument.querySelector('label[for=' + attrQuote(el.id) + ']');
        if (lab) txt = clean(lab.textContent);
      } catch (e) { /* id invalid */ }
    }
    if (!txt) {
      var p = el.closest ? el.closest('label') : null;
      if (p) {
        // textul etichetei fara textul campului insusi
        var clone = p.cloneNode(true);
        Array.prototype.forEach.call(clone.querySelectorAll('input,select,textarea'), function (n) { n.remove(); });
        txt = clean(clone.textContent);
      }
    }
    if (!txt) {
      var ids = el.getAttribute('aria-labelledby');
      if (ids) {
        txt = clean(ids.split(/\s+/).map(function (id) {
          var n = el.ownerDocument.getElementById(id);
          return n ? n.textContent : '';
        }).join(' '));
      }
    }
    return txt;
  }

  function accessibleName(el) {
    var aria = el.getAttribute('aria-label');
    if (clean(aria)) return clean(aria);
    var tag = el.tagName.toLowerCase();
    var isField = tag === 'input' || tag === 'select' || tag === 'textarea';
    var lab = labelText(el);
    if (lab) return lab;
    if (tag === 'img') return clean(el.getAttribute('alt'));
    if (tag === 'input') {
      var type = (el.getAttribute('type') || '').toLowerCase();
      if (type === 'submit' || type === 'button' || type === 'reset') return clean(el.value || el.getAttribute('value'));
      if (type === 'image') return clean(el.getAttribute('alt'));
    }
    if (!isField) {
      var t = clean(el.textContent);
      if (t) return t;
    }
    return clean(el.getAttribute('title') || el.getAttribute('placeholder'));
  }

  // ── 3. Unicitate ──────────────────────────────────────────
  function countCss(doc, sel) {
    try { return doc.querySelectorAll(sel).length; } catch (e) { return 0; }
  }
  function countXPath(doc, xp) {
    try { return doc.evaluate('count(' + xp + ')', doc, null, XPathResult.NUMBER_TYPE, null).numberValue; } catch (e) { return 0; }
  }

  // ── 4. CSS unic, cat mai scurt ────────────────────────────
  function cssSegment(el) {
    var tag = el.tagName.toLowerCase();
    if (el.id && !looksGenerated(el.id)) return '#' + cssEscape(el.id);
    var seg = tag;
    var cls = goodClasses(el);
    if (cls.length) seg += '.' + cls.map(cssEscape).join('.');
    var nameAttr = el.getAttribute('name');
    if (nameAttr && !looksGenerated(nameAttr)) seg += '[name=' + attrQuote(nameAttr) + ']';
    return seg;
  }

  function nthOfType(el) {
    var i = 1, sib = el;
    while ((sib = sib.previousElementSibling)) if (sib.tagName === el.tagName) i++;
    var total = i, n = el;
    while ((n = n.nextElementSibling)) if (n.tagName === el.tagName) total++;
    return total > 1 ? ':nth-of-type(' + i + ')' : '';
  }

  function cssPath(el) {
    var doc = el.ownerDocument;
    var parts = [];
    var cur = el;
    while (cur && cur.nodeType === 1 && cur.tagName.toLowerCase() !== 'html') {
      var seg = cssSegment(cur);
      parts.unshift(seg);
      var sel = parts.join(' > ');
      if (countCss(doc, sel) === 1) return sel;
      if (seg.charAt(0) !== '#') {
        parts[0] = seg + nthOfType(cur);
        sel = parts.join(' > ');
        if (countCss(doc, sel) === 1) return sel;
      }
      cur = cur.parentElement;
    }
    return parts.join(' > ');
  }

  // ── 5. XPath (ancorat pe un id stabil daca exista) ────────
  function xpathOf(el) {
    var parts = [];
    var cur = el;
    while (cur && cur.nodeType === 1) {
      if (cur.id && !looksGenerated(cur.id) && cur !== el) {
        parts.unshift('//*[@id=' + xpathLiteral(cur.id) + ']');
        return parts.join('/');
      }
      var tag = cur.tagName.toLowerCase();
      var i = 1, sib = cur;
      while ((sib = sib.previousElementSibling)) if (sib.tagName === cur.tagName) i++;
      parts.unshift(tag + '[' + i + ']');
      cur = cur.parentElement;
    }
    return '/' + parts.join('/');
  }

  // ── 6. Gasire dupa locator (folosit si pentru verificarea unicitatii) ──
  function allElements(doc) {
    return Array.prototype.slice.call(doc.querySelectorAll('*'));
  }

  function resolve(kind, value, doc) {
    doc = doc || document;
    var res = [];
    try {
      switch (kind) {
        case 'TestId': case 'Css':
          return Array.prototype.slice.call(doc.querySelectorAll(value));
        case 'Id':
          var byId = doc.getElementById(value);
          return byId ? [byId] : [];
        case 'Name':
          return Array.prototype.slice.call(doc.querySelectorAll('[name=' + attrQuote(value) + ']'));
        case 'Placeholder':
          return Array.prototype.slice.call(doc.querySelectorAll('[placeholder=' + attrQuote(value) + ']'));
        case 'XPath':
          var it = doc.evaluate(value, doc, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
          for (var i = 0; i < it.snapshotLength; i++) res.push(it.snapshotItem(i));
          return res;
        case 'Role':
          var p = value.indexOf('|');
          var role = p >= 0 ? value.slice(0, p) : value;
          var name = p >= 0 ? value.slice(p + 1) : null;
          return allElements(doc).filter(function (e) {
            return roleOf(e) === role && (name === null || accessibleName(e) === name) && visible(e);
          });
        case 'Label':
          return Array.prototype.slice.call(doc.querySelectorAll('input,select,textarea,[contenteditable="true"]')).filter(function (e) {
            return labelText(e) === value || clean(e.getAttribute('aria-label')) === value;
          });
        case 'Text':
          // cel mai adanc element al carui text e exact valoarea
          return allElements(doc).filter(function (e) {
            if (clean(e.textContent) !== value || !visible(e)) return false;
            for (var c = e.firstElementChild; c; c = c.nextElementSibling)
              if (clean(c.textContent) === value) return false;
            return true;
          });
      }
    } catch (e) { /* locator invalid */ }
    return res;
  }

  function visible(e) {
    if (!e.getBoundingClientRect) return false;
    var r = e.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) return false;
    var st = window.getComputedStyle ? window.getComputedStyle(e) : null;
    return !st || (st.visibility !== 'hidden' && st.display !== 'none');
  }

  // ── 7. Generarea locatorilor pentru un element ────────────
  var TESTID_ATTRS = ['data-testid', 'data-test-id', 'data-test', 'data-qa', 'data-cy', 'data-automation-id'];

  function generate(el) {
    var doc = el.ownerDocument;
    var tag = el.tagName.toLowerCase();
    var type = (el.getAttribute('type') || '').toLowerCase();
    var locs = [];
    function add(kind, value, score) {
      if (!value) return;
      for (var i = 0; i < locs.length; i++) if (locs[i].kind === kind && locs[i].value === value) return;
      locs.push({ kind: kind, value: value, score: score });
    }
    function uniqueBy(kind, value) {
      var found = resolve(kind, value, doc);
      return found.length === 1 && found[0] === el;
    }

    // 1. atribute de test
    TESTID_ATTRS.forEach(function (a) {
      var v = el.getAttribute(a);
      if (v) {
        var sel = '[' + a + '=' + attrQuote(v) + ']';
        if (countCss(doc, sel) === 1) add('TestId', sel, 95);
      }
    });

    // 2. id stabil
    if (el.id && !looksGenerated(el.id) && uniqueBy('Id', el.id)) add('Id', el.id, 90);

    // 3. rol + nume accesibil
    var role = roleOf(el);
    var name = accessibleName(el);
    if (role && name && name.length <= 80 && uniqueBy('Role', role + '|' + name)) add('Role', role + '|' + name, 85);

    // 4. eticheta campului
    var isField = tag === 'input' || tag === 'select' || tag === 'textarea';
    var lab = isField ? labelText(el) : '';
    if (lab && uniqueBy('Label', lab)) add('Label', lab, 80);

    // 5. name
    var nm = el.getAttribute('name');
    if (nm && !looksGenerated(nm) && uniqueBy('Name', nm)) add('Name', nm, 75);

    // 6. placeholder
    var ph = el.getAttribute('placeholder');
    if (ph && uniqueBy('Placeholder', ph)) add('Placeholder', ph, 70);

    // 7. text vizibil (scurt)
    if (!isField) {
      var txt = clean(el.textContent);
      if (txt && txt.length <= 50 && uniqueBy('Text', txt)) add('Text', txt, 65);
    }

    // 8. CSS + XPath (mereu, ca rezerva)
    var css = cssPath(el);
    if (countCss(doc, css) === 1) add('Css', css, 45);
    var xp = xpathOf(el);
    add('XPath', xp, countXPath(doc, xp) === 1 ? 30 : 10);

    locs.sort(function (a, b) { return b.score - a.score; });

    // ── atribute utile pentru diagnostic ──
    var attrs = {};
    Array.prototype.forEach.call(el.attributes || [], function (a) {
      if (a.value.length <= 200 && !/^on/.test(a.name) && a.name !== 'style') attrs[a.name] = a.value;
    });

    var r = el.getBoundingClientRect();
    return {
      tag: tag,
      type: type,
      role: role || '',
      name: name,
      text: short(isField ? (el.value || '') : el.textContent, 200),
      label: lab,
      suggestedName: suggestName(el, role, name || lab || ph || nm || el.id || tag),
      locators: locs,
      attributes: attrs,
      url: location.href,
      rect: { x: Math.round(r.left), y: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height) }
    };
  }

  function suggestName(el, role, base) {
    var tag = el.tagName.toLowerCase();
    var type = (el.getAttribute('type') || '').toLowerCase();
    var prefix =
      role === 'button' ? 'Buton' :
      role === 'link' ? 'Link' :
      role === 'checkbox' ? 'Bifa' :
      role === 'radio' ? 'Optiune' :
      role === 'combobox' || role === 'listbox' || tag === 'select' ? 'Lista' :
      role === 'textbox' || role === 'searchbox' || role === 'spinbutton' || tag === 'textarea' || type === 'password' ? 'Camp' :
      role === 'heading' ? 'Titlu' :
      role === 'img' ? 'Imagine' :
      tag === 'table' ? 'Tabel' :
      tag === 'td' || tag === 'th' ? 'Celula' :
      'Element';
    var b = short(base, 30)
      .normalize('NFD').replace(/[̀-ͯ]/g, '')
      .replace(/[^A-Za-z0-9]+/g, '_').replace(/^_+|_+$/g, '');
    return b ? prefix + '_' + b : prefix;
  }

  // ── 8. Overlay de marcare ─────────────────────────────────
  var box = null, tip = null;

  function ensureOverlay() {
    if (box && box.isConnected) return;
    box = document.createElement('div');
    box.setAttribute('data-apdc', 'box');
    box.style.cssText = 'position:fixed;pointer-events:none;z-index:' + Z +
      ';border:2px solid ' + COLOR_SPY + ';background:rgba(0,215,160,0.12);border-radius:3px;' +
      'box-shadow:0 0 0 1px rgba(0,0,0,.35);transition:all 60ms ease-out;display:none;';
    tip = document.createElement('div');
    tip.setAttribute('data-apdc', 'tip');
    tip.style.cssText = 'position:fixed;pointer-events:none;z-index:' + Z +
      ';font:12px/1.35 Segoe UI,Arial,sans-serif;color:#fff;background:#000028;padding:4px 8px;' +
      'border-radius:4px;max-width:420px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:none;';
    (document.body || document.documentElement).appendChild(box);
    (document.body || document.documentElement).appendChild(tip);
  }

  function place(el, color, label) {
    ensureOverlay();
    var r = el.getBoundingClientRect();
    box.style.borderColor = color;
    box.style.background = color === COLOR_SPY ? 'rgba(0,215,160,0.12)' : color === COLOR_REC ? 'rgba(224,82,82,0.12)' : color === COLOR_HOVER ? 'rgba(59,130,246,0.14)' : 'rgba(255,153,0,0.15)';
    box.style.left = (r.left - 2) + 'px';
    box.style.top = (r.top - 2) + 'px';
    box.style.width = (r.width + 4) + 'px';
    box.style.height = (r.height + 4) + 'px';
    box.style.display = 'block';
    if (label) {
      tip.textContent = label;
      tip.style.left = Math.max(2, r.left) + 'px';
      tip.style.top = (r.top > 26 ? r.top - 24 : r.bottom + 4) + 'px';
      tip.style.display = 'block';
    } else if (tip) {
      tip.style.display = 'none';
    }
  }

  function hideOverlay() {
    if (box) box.style.display = 'none';
    if (tip) tip.style.display = 'none';
  }

  // Marcare temporara (la rulare, inainte de actiune)
  var hlTimer = null;
  function highlight(el, ms) {
    if (!el) return false;
    try { el.scrollIntoView({ block: 'nearest', inline: 'nearest' }); } catch (e) { /* ignorat */ }
    place(el, COLOR_RUN, null);
    clearTimeout(hlTimer);
    hlTimer = setTimeout(hideOverlay, ms || 600);
    return true;
  }

  // ── 9. Spy / Recorder ─────────────────────────────────────
  var mode = null, hint = '', current = null;

  function isOurs(el) {
    return el && el.getAttribute && el.getAttribute('data-apdc') !== null;
  }

  function targetOf(ev) {
    var path = ev.composedPath ? ev.composedPath() : [ev.target];
    for (var i = 0; i < path.length; i++)
      if (path[i] && path[i].nodeType === 1 && !isOurs(path[i])) return path[i];
    return null;
  }

  // urcam de la <span> din buton la butonul insusi
  function interactiveAncestor(el) {
    var cur = el;
    for (var i = 0; cur && i < 4; i++, cur = cur.parentElement) {
      var r = roleOf(cur);
      if (r === 'button' || r === 'link' || r === 'checkbox' || r === 'radio' || r === 'option' || r === 'menuitem' || r === 'tab') return cur;
      var t = cur.tagName.toLowerCase();
      if (t === 'input' || t === 'select' || t === 'textarea' || t === 'label') return cur;
    }
    return el;
  }

  function emit(payload) {
    var json = JSON.stringify(payload);
    if (typeof window.__apdcEmit === 'function') {
      try { window.__apdcEmit(json); return; } catch (e) { /* cadem pe coada */ }
    }
    api.queue.push(json);
  }

  // ── captura cu cursorul tinut pe element (mode 'hover') ──
  var HOVER_MS = 3000;
  var hoverTimer = null, hoverTick = null, hoverStart = 0, hoverDone = null, hoverName = '';

  function hoverReset() {
    clearTimeout(hoverTimer);
    clearInterval(hoverTick);
    hoverTimer = hoverTick = null;
  }

  function hoverArm(el, name) {
    hoverReset();
    if (el === hoverDone) {          // deja capturat: mutati cursorul pe alt element
      place(el, COLOR_HOVER, '✔ ' + name + (hint ? '   ·   ' + hint : ''));
      return;
    }
    hoverStart = Date.now();
    hoverName = name;
    function label() {
      var left = Math.max(0, Math.ceil((HOVER_MS - (Date.now() - hoverStart)) / 1000));
      place(el, COLOR_HOVER, '⏱ ' + left + ' s   ·   ' + hoverName + (hint ? '   ·   ' + hint : ''));
    }
    label();
    hoverTick = setInterval(function () { if (current === el && el.isConnected) label(); }, 250);
    hoverTimer = setTimeout(function () {
      hoverReset();
      if (mode !== 'hover' || current !== el || !el.isConnected) return;
      hoverDone = el;
      emit({ type: 'captured', element: generate(el) });
      place(el, COLOR_HOVER, '✔ ' + hoverName + (hint ? '   ·   ' + hint : ''));
    }, HOVER_MS);
  }

  function onMove(ev) {
    var el = targetOf(ev);
    if (!el) return;
    el = interactiveAncestor(el);
    if (mode === 'hover' && el === current) return;   // acelasi element: numaratoarea continua
    current = el;
    var g = generate(el);
    if (mode === 'hover') { hoverArm(el, g.suggestedName); return; }
    var best = g.locators.length ? g.locators[0] : null;
    var label = g.suggestedName + (best ? '   ·   ' + best.kind + ': ' + short(best.value, 60) : '') + (hint ? '   ·   ' + hint : '');
    place(el, mode === 'record' ? COLOR_REC : COLOR_SPY, label);
  }

  function swallow(ev) {
    ev.preventDefault();
    ev.stopPropagation();
    if (ev.stopImmediatePropagation) ev.stopImmediatePropagation();
  }

  function onClickCapture(ev) {
    var el = targetOf(ev);
    if (!el) return;
    el = interactiveAncestor(el);
    if (mode === 'spy') {
      swallow(ev);
      emit({ type: 'captured', element: generate(el) });
      return;
    }
    if (mode === 'record') {
      var tag = el.tagName.toLowerCase();
      var type = (el.getAttribute('type') || '').toLowerCase();
      // campurile text si listele se inregistreaza la "change" (valoarea), nu la click
      var isTextField = (tag === 'input' && ['', 'text', 'email', 'tel', 'url', 'search', 'number', 'password', 'date'].indexOf(type) >= 0) || tag === 'textarea' || tag === 'select';
      if (isTextField || type === 'checkbox' || type === 'radio') return;
      emit({ type: 'action', action: ev.detail === 2 ? 'DoubleClick' : 'Click', value: '', element: generate(el) });
    }
  }

  function onBlockedMouse(ev) {
    if (mode === 'spy') swallow(ev);
  }

  function onChange(ev) {
    if (mode !== 'record') return;
    var el = targetOf(ev);
    if (!el) return;
    var tag = el.tagName.toLowerCase();
    var type = (el.getAttribute('type') || '').toLowerCase();
    if (tag === 'select') {
      var opt = el.options[el.selectedIndex];
      emit({ type: 'action', action: 'SelectOption', value: opt ? clean(opt.text) : '', element: generate(el) });
    } else if (type === 'checkbox' || type === 'radio') {
      emit({ type: 'action', action: el.checked ? 'Check' : 'Uncheck', value: '', element: generate(el) });
    } else if (tag === 'input' || tag === 'textarea') {
      emit({ type: 'action', action: 'TypeText', value: el.value, element: generate(el) });
    }
  }

  function onKey(ev) {
    if (ev.key === 'Escape' && mode) {
      swallow(ev);
      emit({ type: mode === 'spy' ? 'cancel' : 'stop' });   // 'record' si 'hover' -> stop
      stopSpy();
      return;
    }
    // Enter in record = apasare tasta pe camp (ex: cautare)
    if (mode === 'record' && ev.key === 'Enter') {
      var el = targetOf(ev);
      if (el && (el.tagName.toLowerCase() === 'input')) {
        emit({ type: 'action', action: 'TypeText', value: el.value, element: generate(el) });
        emit({ type: 'action', action: 'PressKey', value: 'Enter', element: generate(el) });
      }
    }
  }

  function startSpy(m, h) {
    stopSpy();
    mode = m === 'record' ? 'record' : m === 'hover' ? 'hover' : 'spy';
    hint = h || '';
    hoverDone = null;
    document.addEventListener('mousemove', onMove, true);
    document.addEventListener('keydown', onKey, true);
    if (mode === 'hover') return true;   // click-urile si scrierea trec normal in pagina
    document.addEventListener('click', onClickCapture, true);
    document.addEventListener('dblclick', onBlockedMouse, true);
    document.addEventListener('mousedown', onBlockedMouse, true);
    document.addEventListener('mouseup', onBlockedMouse, true);
    document.addEventListener('pointerdown', onBlockedMouse, true);
    document.addEventListener('pointerup', onBlockedMouse, true);
    document.addEventListener('change', onChange, true);
    document.addEventListener('keydown', onKey, true);
    return true;
  }

  function stopSpy() {
    mode = null;
    current = null;
    hoverReset();
    hoverDone = null;
    document.removeEventListener('mousemove', onMove, true);
    document.removeEventListener('click', onClickCapture, true);
    document.removeEventListener('dblclick', onBlockedMouse, true);
    document.removeEventListener('mousedown', onBlockedMouse, true);
    document.removeEventListener('mouseup', onBlockedMouse, true);
    document.removeEventListener('pointerdown', onBlockedMouse, true);
    document.removeEventListener('pointerup', onBlockedMouse, true);
    document.removeEventListener('change', onChange, true);
    document.removeEventListener('keydown', onKey, true);
    hideOverlay();
    return true;
  }

  // Selector pentru un <iframe> (cerut de pagina parinte cand elementul e intr-un iframe)
  function frameSelector(frameEl) {
    var n = frameEl.getAttribute('name');
    if (n && !looksGenerated(n) && countCss(frameEl.ownerDocument, 'iframe[name=' + attrQuote(n) + ']') === 1)
      return 'iframe[name=' + attrQuote(n) + ']';
    if (frameEl.id && !looksGenerated(frameEl.id)) return '#' + cssEscape(frameEl.id);
    var t = frameEl.getAttribute('title');
    if (t && countCss(frameEl.ownerDocument, frameEl.tagName.toLowerCase() + '[title=' + attrQuote(t) + ']') === 1)
      return frameEl.tagName.toLowerCase() + '[title=' + attrQuote(t) + ']';
    return cssPath(frameEl);
  }

  // ── 10. Scanarea paginii (v4.9) ───────────────────────────
  // Doar citeste DOM-ul deja incarcat: nu da click, nu scrie, nu trimite cereri.
  // Lucrul e impartit in loturi mici (scanBatch), ca pagina sa ramana fluida.
  var SCAN_SELECTOR = [
    'button', 'a[href]', 'select', 'textarea', 'input:not([type=hidden])', '[contenteditable="true"]',
    '[role=button]', '[role=link]', '[role=checkbox]', '[role=radio]', '[role=combobox]', '[role=textbox]',
    '[role=searchbox]', '[role=tab]', '[role=menuitem]', '[role=switch]', '[role=option]', '[role=spinbutton]'
  ].join(',');
  var scanList = [];

  function scanVisible(e) {
    if (isOurs(e)) return false;
    var r = e.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) return false;
    var st = window.getComputedStyle ? getComputedStyle(e) : null;
    // si elementele dezactivate conteaza: devin active mai tarziu
    return !(st && (st.visibility === 'hidden' || st.display === 'none' || st.opacity === '0'));
  }

  function scanStart(max) {
    max = max || 500;
    var seen = [], out = [];
    var all = document.querySelectorAll(SCAN_SELECTOR);
    for (var i = 0; i < all.length && out.length < max; i++) {
      var el = interactiveAncestor(all[i]);
      if (seen.indexOf(el) >= 0 || !scanVisible(el)) continue;
      seen.push(el);
      out.push(el);
    }
    scanList = out;
    return { found: out.length, total: all.length };
  }

  function scanBatch(start, n) {
    var res = [];
    for (var i = start; i < scanList.length && i < start + n; i++) {
      try { res.push(generate(scanList[i])); } catch (e) { /* element disparut */ }
    }
    if (start + n >= scanList.length) scanList = [];
    return res;
  }

  function drain() {
    var q = api.queue.slice();
    api.queue.length = 0;
    return JSON.stringify(q);
  }

  var api = {
    version: 2,
    queue: [],
    generate: generate,
    resolve: resolve,
    roleOf: roleOf,
    accessibleName: accessibleName,
    cssPath: cssPath,
    xpathOf: xpathOf,
    frameSelector: frameSelector,
    highlight: highlight,
    startSpy: startSpy,
    scanStart: scanStart,
    scanBatch: scanBatch,
    stopSpy: stopSpy,
    drain: drain,
    looksGenerated: looksGenerated,
    isActive: function () { return mode; }
  };
  window.__apdc = api;
})();
