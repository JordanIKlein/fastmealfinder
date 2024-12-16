// script.js
const canvas = document.getElementById('emojiCanvas');
const ctx = canvas.getContext('2d');

// Resize canvas to fit the screen
canvas.width = window.innerWidth;
canvas.height = window.innerHeight;

// Emoji options
const emojis = ['🍔', '🍟', '🌭', '🍕', '🥤','🌯', '🌮','🍪']; 

// Array to store particles
const particles = [];

// Particle class
class Particle {
    constructor() {
        this.x = Math.random() * canvas.width; // Random initial position (x-axis)
        this.y = Math.random() * canvas.height; // Random initial position (y-axis)
        this.size = Math.random() * 40 + 10; // Random size between 10px and 50px
        this.speedX = Math.random() * 1.5 - 0.75; // Random horizontal speed (-0.75 to 0.75)
        this.speedY = Math.random() * 1.5 - 0.75; // Random vertical speed (-0.75 to 0.75)
        this.emoji = emojis[Math.floor(Math.random() * emojis.length)]; // Random emoji
    }

    draw() {
        // Draw emoji at the particle's current position
        ctx.font = `${this.size}px Arial`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(this.emoji, this.x, this.y);
    }

    update() {
        // Update position
        this.x += this.speedX;
        this.y += this.speedY;

        // Bounce off edges
        if (this.x < 0 || this.x > canvas.width) this.speedX *= -1;
        if (this.y < 0 || this.y > canvas.height) this.speedY *= -1;
    }
}

// Initialize particles
function initParticles() {
    for (let i = 0; i < 75; i++) { // Add 75 particles
        particles.push(new Particle());
    }
}

// Animate particles
function animateParticles() {
    // Clear the canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw and update each particle
    particles.forEach((particle) => {
        particle.update();
        particle.draw();
    });

    // Loop animation
    requestAnimationFrame(animateParticles);
}



// Smooth resizing without clearing particles
window.addEventListener('resize', () => {
    const oldWidth = canvas.width;
    const oldHeight = canvas.height;

    // Update canvas size
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;

    // Adjust existing particles' positions proportionally
    const widthRatio = canvas.width / oldWidth;
    const heightRatio = canvas.height / oldHeight;

    particles.forEach((particle) => {
        particle.x *= widthRatio;
        particle.y *= heightRatio;
    });
});


// Initialize and start animation
initParticles();
animateParticles();





  