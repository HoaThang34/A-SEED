// IntersectionObserver-based reveal-on-scroll.
// Each .fx-reveal element gets .is-visible once it enters the viewport,
// with a small stagger (index * 100ms) for pleasant sequencing.
document.addEventListener('DOMContentLoaded', () => {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry, index) => {
      if (entry.isIntersecting) {
        setTimeout(() => entry.target.classList.add('is-visible'), index * 100);
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1 });

  document.querySelectorAll('.fx-reveal').forEach(el => observer.observe(el));
});
