// State & Data
const products = JSON.parse(document.getElementById('products-data').textContent || '[]');

let selectedProduct = products[0] || null;
let selectedSize = "P";
let activeCategory = "Todos";
let cart = loadCart();

// Helpers
const money = v => v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

// Navigation System
function navigate(viewName) {
  document.querySelectorAll('.view').forEach(el => el.classList.remove('active'));
  document.getElementById('view-' + viewName).classList.add('active');

  document.querySelectorAll('.nav button').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.view === viewName);
  });

  if (viewName === 'shop') renderShop();
  if (viewName === 'cart') renderCart();

  window.scrollTo({ top: 0, behavior: 'smooth' });
  history.replaceState(null, '', '#' + viewName);
}

// Component Renders
function card(p) {
  return `
    <article class="product-card" onclick="openProduct(${p.id})">
      <div class="card-img">
        <img src="${p.images[0]}" alt="${p.name}">
      </div>
      <div class="card-body">
        <p class="meta">${p.collection} · ${p.category}</p>
        <h3>${p.name}</h3>
        <p class="price">${money(p.price)}</p>
      </div>
    </article>
  `;
}

function renderHome() {
  document.getElementById('home-grid').innerHTML = products.filter(p => p.destaque).slice(0, 3).map(card).join('');
}

function renderShop() {
  const cats = [...new Set(products.map(p => p.category))];
  const filters = document.getElementById('filters');

  if (cats.length > 1) {
    filters.classList.remove('hidden');
    filters.innerHTML = ['Todos', ...cats].map(c => `
      <button class="filter ${activeCategory === c ? 'active' : ''}" onclick="setCategory('${c}')">${c}</button>
    `).join('');
  } else {
    filters.classList.add('hidden');
    filters.innerHTML = '';
  }

  const list = activeCategory === 'Todos' ? products : products.filter(p => p.category === activeCategory);
  document.getElementById('product-count').textContent = `${list.length} ${list.length === 1 ? 'produto' : 'produtos'}`;
  document.getElementById('shop-grid').innerHTML = list.map(card).join('');
}

function setCategory(category) {
  activeCategory = category;
  renderShop();
}

function openCollection(collectionSlug) {
  navigate('shop');
  const list = products.filter(p => p.collectionSlug === collectionSlug);
  document.getElementById('product-count').textContent = `${list.length} ${list.length === 1 ? 'produto' : 'produtos'}`;
  document.getElementById('shop-grid').innerHTML = list.map(card).join('');
}

function openProduct(id) {
  selectedProduct = products.find(p => p.id === id) || products[0];
  const availableSize = selectedProduct.sizes.find(
    size => selectedProduct.stock[size] > 0
  );

selectedSize = availableSize || null;

  document.getElementById('breadcrumb').textContent = `${selectedProduct.collection} / ${selectedProduct.category}`;
  document.getElementById('product-name').textContent = selectedProduct.name;
  document.getElementById('product-price').textContent = money(selectedProduct.price);
  document.getElementById('product-desc').textContent = selectedProduct.description;
  document.getElementById('main-image').src = selectedProduct.images[0];
  document.getElementById('main-image').alt = selectedProduct.name;

  document.getElementById('thumbs').innerHTML = selectedProduct.images.map((img, i) => `
    <button class="thumb ${i === 0 ? 'active' : ''}" onclick="changeImage('${img}', this)">
      <img src="${img}" alt="">
    </button>
  `).join('');

  document.getElementById('sizes').innerHTML = selectedProduct.sizes.map((s) => {

      const estoque = selectedProduct.stock[s] || 0;
      const indisponivel = estoque <= 0;

      return `
          <button
              class="size ${s === selectedSize ? 'active' : ''} ${indisponivel ? 'disabled' : ''}"
              onclick="${indisponivel ? '' : `chooseSize('${s}', this)`}"
              ${indisponivel ? 'disabled' : ''}
          >
              ${s}
          </button>
      `;

  }).join('');

  document.getElementById('selected-size').textContent =
    selectedSize
        ? 'Selecionado: ' + selectedSize
        : 'Sem estoque';
  
  navigate('product');
}

function changeImage(img, btn) {
  document.getElementById('main-image').src = img;
  document.querySelectorAll('.thumb').forEach(x => x.classList.remove('active'));
  btn.classList.add('active');
}

function chooseSize(size, btn) {
  selectedSize = size;
  document.querySelectorAll('.size').forEach(x => x.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById('selected-size').textContent = 'Selecionado: ' + size;
}

// Cart Logic
function loadCart() {
  try {
    return JSON.parse(localStorage.getItem('veredas-cart')) || [];
  } catch {
    return [];
  }
}

function saveCart() {
  try {
    localStorage.setItem('veredas-cart', JSON.stringify(cart));
  } catch {}
}

function countCart() {
  return cart.reduce((acc, item) => acc + item.quantity, 0);
}

function totalCart() {
  return cart.reduce((acc, item) => acc + (item.price * item.quantity), 0);
}

function updateCartCount() {
  document.getElementById('cart-count').textContent = countCart();
}

function addToCart() {

    if (!selectedProduct || !selectedSize) {
        toast('Escolha um tamanho disponível.');
        return;
    }

    const estoque = selectedProduct.stock[selectedSize] || 0;

    const item = cart.find(
        i => i.id === selectedProduct.id && i.size === selectedSize
    );

    const quantidadeAtual = item ? item.quantity : 0;

    if (quantidadeAtual >= estoque) {
        toast('Quantidade máxima disponível em estoque.');
        return;
    }

    if (item) {

        item.quantity++;

    } else {

        cart.push({
            id: selectedProduct.id,
            name: selectedProduct.name,
            price: selectedProduct.price,
            image: selectedProduct.images[0],
            size: selectedSize,
            quantity: 1
        });

    }

    saveCart();
    updateCartCount();

    toast(
        `${selectedProduct.name} — tamanho ${selectedSize} adicionada à sacola.`
    );
}

function changeQty(index, delta) {
  if (!cart[index]) return;
  if (delta > 0) {
    const item = cart[index];
    const produto = products.find(p => p.id === item.id);
    const estoque = produto?.stock?.[item.size] || 0;
    if (item.quantity + delta > estoque) {
      toast('Quantidade máxima disponível em estoque.');
      return;
    }
  }
  cart[index].quantity += delta;
  if (cart[index].quantity <= 0) {
    cart.splice(index, 1);
  }
  saveCart();
  updateCartCount();
  renderCart();
}

function removeItem(index) {
  cart.splice(index, 1);
  saveCart();
  updateCartCount();
  renderCart();
}

function renderCart() {
  const container = document.getElementById('cart-content');

  if (!cart.length) {
    container.innerHTML = `
      <div class="empty">
        <i class="fa-solid fa-bag-shopping"></i>
        <h2>Sua sacola está vazia.</h2>
        <p class="muted">Escolha uma peça na loja para começar seu pedido.</p>
        <button class="primary" onclick="navigate('shop')">Ir para a loja</button>
      </div>
    `;
    return;
  }

  const itemsHTML = cart.map((item, idx) => `
    <article class="cart-item">
      <div class="cart-img">
        <img src="${item.image}" alt="${item.name}">
      </div>
      <div>
        <h3>${item.name}</h3>
        <p class="cart-meta">Tamanho ${item.size}</p>
        <div class="qty">
          <button onclick="changeQty(${idx}, -1)">−</button>
          <span>${item.quantity}</span>
          <button onclick="changeQty(${idx}, 1)">+</button>
        </div>
      </div>
      <div class="cart-side">
        <p class="price">${money(item.price * item.quantity)}</p>
        <button class="remove" onclick="removeItem(${idx})">Remover</button>
      </div>
    </article>
  `).join('');

  const total = totalCart();

  container.innerHTML = `
    <div class="cart-layout">
      <div class="cart-items">${itemsHTML}</div>
      <aside class="summary">
        <h2>Resumo do pedido</h2>
        <div class="summary-row">
          <span>Subtotal</span>
          <strong>${money(total)}</strong>
        </div>
        <div class="summary-row">
          <span>Frete</span>
          <span>Calculado no checkout</span>
        </div>
        <div class="summary-row total">
          <span>Total</span>
          <span>${money(total)}</span>
        </div>
        <button class="checkout" onclick="checkout()">Finalizar pedido</button>
        <p class="muted" style="font-size: .72rem">O valor do frete é definido na etapa de finalização.</p>
      </aside>
    </div>
  `;
}

async function validarEstoqueCarrinho() {
  const itens = cart.map(({ id, size, quantity }) => ({ id, size, quantity }));
  try {
    const csrfCookie = document.cookie.split('; ').find(cookie => cookie.startsWith('csrftoken='));
    const response = await fetch('/api/validar-estoque/', {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfCookie ? decodeURIComponent(csrfCookie.split('=')[1]) : ''
      },
      body: JSON.stringify({ itens })
    });
    const resultado = await response.json();
    if (!response.ok) {
      toast(resultado.erro || 'Não foi possível validar o estoque. Tente novamente.');
      return false;
    }
    if (!resultado.valido) {
      toast(resultado.erros.map(item =>
        `${item.produto} — tamanho ${item.tamanho}: solicitado ${item.quantidade_solicitada}, disponível ${item.quantidade_disponivel}.`
      ).join(' '));
      return false;
    }
    if (JSON.stringify(itens) !== JSON.stringify(cart.map(({ id, size, quantity }) => ({ id, size, quantity })))) {
      toast('A sacola foi alterada. Valide o estoque novamente.');
      return false;
    }
    return true;
  } catch {
    toast('Não foi possível validar o estoque. Tente novamente.');
    return false;
  }
}

async function checkout() {
  if (!await validarEstoqueCarrinho()) return;
  alert('Checkout ainda não configurado.');
}

// UI Feedback
function toast(message) {
  const toastEl = document.getElementById('toast');
  toastEl.textContent = message;
  toastEl.classList.add('show');
  clearTimeout(window.__toast);
  window.__toast = setTimeout(() => toastEl.classList.remove('show'), 2600);
}

// Mobile Menu Controls
function openMenu() {
  document.getElementById('mobile-menu').classList.add('open');
}

function closeMenu() {
  document.getElementById('mobile-menu').classList.remove('open');
}

function backdropClose(e) {
  if (e.target.id === 'mobile-menu') closeMenu();
}

// ==========================================
// HERO CAROUSEL SYSTEM
// ==========================================
let currentHeroSlide = 0;
const totalHeroSlides = 2;
let heroAutoplayTimer = null;
const HERO_AUTOPLAY_INTERVAL = 6500;

function updateHeroCarousel() {
  const track = document.getElementById('hero-track');
  if (!track) return;

  track.style.transform = `translateX(-${currentHeroSlide * 100}%)`;

  const slides = document.querySelectorAll('.hero-slide');
  slides.forEach((slide, idx) => {
    const isActive = idx === currentHeroSlide;
    slide.classList.toggle('active', isActive);
    slide.setAttribute('aria-hidden', (!isActive).toString());
  });

  const dots = document.querySelectorAll('.hero-dot');
  dots.forEach((dot, idx) => {
    const isActive = idx === currentHeroSlide;
    dot.classList.toggle('active', isActive);
    dot.setAttribute('aria-selected', isActive.toString());
  });
}

function goToHeroSlide(index) {
  if (index < 0 || index >= totalHeroSlides) return;
  currentHeroSlide = index;
  updateHeroCarousel();
  resetHeroAutoplay();
}

function nextHeroSlide() {
  currentHeroSlide = (currentHeroSlide + 1) % totalHeroSlides;
  updateHeroCarousel();
  resetHeroAutoplay();
}

function prevHeroSlide() {
  currentHeroSlide = (currentHeroSlide - 1 + totalHeroSlides) % totalHeroSlides;
  updateHeroCarousel();
  resetHeroAutoplay();
}

function startHeroAutoplay() {
  stopHeroAutoplay();
  heroAutoplayTimer = setInterval(() => {
    currentHeroSlide = (currentHeroSlide + 1) % totalHeroSlides;
    updateHeroCarousel();
  }, HERO_AUTOPLAY_INTERVAL);
}

function stopHeroAutoplay() {
  if (heroAutoplayTimer) {
    clearInterval(heroAutoplayTimer);
    heroAutoplayTimer = null;
  }
}

function resetHeroAutoplay() {
  stopHeroAutoplay();
  startHeroAutoplay();
}

function initHeroCarousel() {
  const carousel = document.getElementById('hero-carousel');
  if (!carousel) return;

  updateHeroCarousel();
  startHeroAutoplay();

  carousel.addEventListener('mouseenter', stopHeroAutoplay);
  carousel.addEventListener('mouseleave', startHeroAutoplay);
  carousel.addEventListener('focusin', stopHeroAutoplay);
  carousel.addEventListener('focusout', startHeroAutoplay);

  carousel.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowLeft') {
      prevHeroSlide();
    } else if (e.key === 'ArrowRight') {
      nextHeroSlide();
    }
  });

  let touchStartX = 0;
  let touchStartY = 0;
  let touchEndX = 0;
  let touchEndY = 0;

  carousel.addEventListener('touchstart', (e) => {
    touchStartX = e.changedTouches[0].screenX;
    touchStartY = e.changedTouches[0].screenY;
    stopHeroAutoplay();
  }, { passive: true });

  carousel.addEventListener('touchend', (e) => {
    touchEndX = e.changedTouches[0].screenX;
    touchEndY = e.changedTouches[0].screenY;
    const diffX = touchEndX - touchStartX;
    const diffY = touchEndY - touchStartY;
    if (Math.abs(diffX) > Math.abs(diffY) && Math.abs(diffX) > 40) {
      if (diffX < 0) {
        nextHeroSlide();
      } else {
        prevHeroSlide();
      }
    }
    startHeroAutoplay();
  }, { passive: true });
}

// Initialization
renderHome();
renderShop();
updateCartCount();
initHeroCarousel();

const initialRoute = location.hash.replace('#', '');
if (['home', 'shop', 'collections', 'about', 'cart'].includes(initialRoute)) {
  navigate(initialRoute);
} else {
  navigate('home');
}
