
 window.onload = () => {
    const grid = document.querySelector('.post-container');
    const masonry = new Masonry(grid,{
        itemSelector: '.post-item',
        columnWidth: 200,
        gutter: 10, //padding
        percentPosition: true,
        originRight: true,
    });
};
  
  