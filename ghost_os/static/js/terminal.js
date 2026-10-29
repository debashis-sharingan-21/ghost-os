/**
 * GHOST.OS — Retro CRT Terminal Console Manager
 */

class GhostTerminal {
  constructor(containerId, maxLines = 100) {
    this.container = document.getElementById(containerId);
    this.maxLines = maxLines;
  }

  log(msg, level = 'info') {
    if (!this.container) return;

    const line = document.createElement('div');
    line.className = 'log-line';

    const now = new Date();
    const tsStr = now.toTimeString().split(' ')[0] + '.' + String(now.getMilliseconds()).padStart(3, '0');

    const tsSpan = document.createElement('span');
    tsSpan.className = 'log-ts';
    tsSpan.textContent = `[${tsStr}]`;

    const msgSpan = document.createElement('span');
    msgSpan.className = `log-${level}`;
    msgSpan.textContent = msg;

    line.appendChild(tsSpan);
    line.appendChild(msgSpan);

    this.container.appendChild(line);

    while (this.container.children.length > this.maxLines) {
      this.container.removeChild(this.container.firstChild);
    }

    this.container.scrollTop = this.container.scrollHeight;
  }

  info(msg) { this.log(msg, 'info'); }
  warn(msg) { this.log(msg, 'warn'); }
  crit(msg) { this.log(msg, 'crit'); }
  sys(msg)  { this.log(msg, 'sys'); }

  clear() {
    if (this.container) {
      this.container.innerHTML = '';
    }
  }
}
