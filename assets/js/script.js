const menuButton = document.querySelector('.menu-btn');
const navigation = document.querySelector('.nav-links');
menuButton.addEventListener('click', () => {
  const open = navigation.classList.toggle('open');
  menuButton.setAttribute('aria-expanded', open);
});
document.querySelectorAll('.nav-links a').forEach(link => link.addEventListener('click', () => navigation.classList.remove('open')));

const observer = new IntersectionObserver(entries => entries.forEach(entry => {
  if (entry.isIntersecting) { entry.target.classList.add('visible'); observer.unobserve(entry.target); }
}), { threshold: .12 });
document.querySelectorAll('.reveal').forEach(element => observer.observe(element));

document.querySelector('#resource-form').addEventListener('submit', event => {
  event.preventDefault();
  const note = document.querySelector('#form-note');
  note.textContent = '✓ You’re on the list! Your study pack is on its way.';
  note.style.color = '#4e7900';
  event.target.reset();
});
