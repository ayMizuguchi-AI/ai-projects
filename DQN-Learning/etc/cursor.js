const cursorSF = document.getElementById('startMenuCursorSf');
const cursorLight = document.getElementById('startMenuCursorLight');

window.addEventListener('mousemove', (e) => {
    const x = e.clientX;
    const y = e.clientY;

    const translateValue = `translate(${x}px, ${y}px)`;

    cursorSF.style.transform = `${translateValue} translate(-50%, -50%)`;
    cursorLight.style.transform = `${translateValue} translate(-50%, -50%)`;
});

const buttons = document.querySelectorAll('.clickable');
buttons.forEach(btn => {
    btn.addEventListener('mouseenter', () => {
        document.body.classList.add('cursor-hover');
    });
    btn.addEventListener('mouseleave', () => {
        document.body.classList.remove('cursor-hover');
    });
});

window.addEventListener('mousedown', () => {
    document.body.classList.add('cursor-active');
});
window.addEventListener('mouseup', () => {
    document.body.classList.remove('cursor-active');
});

//マウスがウィンドウに入ったとき
document.addEventListener('mouseenter', () => {
    document.body.classList.add('mouse-in');
});
//マウスがウィンドウから出たとき
document.addEventListener('mouseleave', () => {
    document.body.classList.remove('mouse-in');
});