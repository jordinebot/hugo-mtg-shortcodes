/* MTG shortcodes runtime:
   1. Flip-card toggle for double-faced cards (the `card` / `cardname` shortcodes).
   2. Smart positioning of `cardname` hover previews so the 240px preview
      stays inside the viewport even when the cardname sits near an edge.
      The CSS exposes `--preview-shift` (horizontal nudge) and
      `.cardname__preview--above` (flip vertically); this script drives them.
*/

/* ---------- 1. Flip toggle ---------- */

document.addEventListener('click', (event) => {
  const flipBtn = event.target.closest('.js-flip-toggle');
  if (!flipBtn) return;
  const flippable = flipBtn.closest('.js-flippable');
  if (!flippable) return;
  const flipped = flippable.classList.toggle('is-flipped');
  flipBtn.setAttribute('aria-pressed', String(flipped));
});

/* ---------- 2. Preview positioning ---------- */

const PREVIEW_MARGIN = 8; // px buffer kept between preview and viewport edge

function shiftPreviewHorizontally(cardname) {
  const preview = cardname.querySelector('.cardname__preview');
  if (!preview) return;

  // Reset any previous adjustment so we measure the natural position.
  cardname.style.removeProperty('--preview-shift');

  const r = preview.getBoundingClientRect();
  const vw = document.documentElement.clientWidth;

  let shift = 0;
  if (r.right > vw - PREVIEW_MARGIN) {
    shift = (vw - PREVIEW_MARGIN) - r.right;        // negative — pull left
  } else if (r.left < PREVIEW_MARGIN) {
    shift = PREVIEW_MARGIN - r.left;                // positive — push right
  }

  if (shift !== 0) {
    cardname.style.setProperty('--preview-shift', `${shift}px`);
  }
}

function flipPreviewIfNeeded(cardname) {
  const preview = cardname.querySelector('.cardname__preview');
  if (!preview) return;

  preview.classList.remove('cardname__preview--above');
  const r = preview.getBoundingClientRect();
  const vh = document.documentElement.clientHeight;

  if (r.bottom > vh - PREVIEW_MARGIN) {
    preview.classList.add('cardname__preview--above');
  }
}

function adjustAllPreviews() {
  document.querySelectorAll('.cardname').forEach(shiftPreviewHorizontally);
}

function initPreviewPositioning() {
  // Run once after initial layout so invisible previews near the right
  // edge stop pushing the body's scroll width past the viewport.
  adjustAllPreviews();

  // Re-run after fonts load (text reflow can move cardname positions).
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(adjustAllPreviews);
  }

  // Re-run on resize (debounced).
  let resizeTimer;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(adjustAllPreviews, 120);
  });

  // On hover / focus, recompute both axes — viewport-relative position
  // depends on current scroll, so this catches edge cases the static
  // pass can't (e.g. preview crossing the viewport bottom mid-scroll).
  document.querySelectorAll('.cardname').forEach((cn) => {
    const recompute = () => {
      shiftPreviewHorizontally(cn);
      flipPreviewIfNeeded(cn);
    };
    cn.addEventListener('mouseenter', recompute);
    cn.addEventListener('focusin', recompute);
  });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initPreviewPositioning);
} else {
  initPreviewPositioning();
}
