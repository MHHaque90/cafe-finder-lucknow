import '@testing-library/jest-dom/vitest';

// jsdom does not implement Element.scrollIntoView; the app calls it only
// as a progressive enhancement when a marker selects its card.
if (typeof Element.prototype.scrollIntoView !== 'function') {
  Element.prototype.scrollIntoView = function () {};
}
