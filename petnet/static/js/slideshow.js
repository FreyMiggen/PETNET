document.addEventListener('DOMContentLoaded', function() {
    let slideshows = document.querySelectorAll('.slideshow-container');
    slideshows.forEach(function(slideshow) {
        let slides = slideshow.querySelectorAll('.slide');
        if (slides.length > 0) {
            showSlide(slides, 0);
        }
    });
});

function plusSlides(element, n) {
    let slideshow = element.closest('.slideshow-container');
    let slides = slideshow.querySelectorAll('.slide');
    let currentIndex = Array.from(slides).findIndex(slide => slide.style.display === 'block');
    let newIndex = (currentIndex + n + slides.length) % slides.length;
    showSlide(slides, newIndex);
}

function showSlide(slides, index) {
    slides.forEach(slide => slide.style.display = 'none');
    slides[index].style.display = 'block';
}