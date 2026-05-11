/* Flip-card toggle for double-faced cards rendered by the `card` and
   `cardname` shortcodes. */
document.addEventListener('click', (event) => {
  const flipBtn = event.target.closest('.js-flip-toggle');
  if (!flipBtn) return;
  const flippable = flipBtn.closest('.js-flippable');
  if (!flippable) return;
  const flipped = flippable.classList.toggle('is-flipped');
  flipBtn.setAttribute('aria-pressed', String(flipped));
});
