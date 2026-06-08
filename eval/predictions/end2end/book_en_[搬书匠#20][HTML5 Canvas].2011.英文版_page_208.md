function canvasApp() {
  if (!canvasSupport()) {
    return;
  }
  function drawScreen () {
    context.fillStyle = "#000000";
    context.fillRect(0, 0, theCanvas.width, theCanvas.height);
    //box
    context.strokeStyle = "#000000";
    context.strokeRect(1, 1, theCanvas.width-2, theCanvas.height-2);
    //ball
    context.fillStyle = "#000000";
    context.beginPath();
    context.arc(ball.x,ball.y,15,0,Math.PI*2,true);
    context.fill();
    context.stroke();
    context.fill();
  }
  if (ball.x > theCanvas.width || ball.x < 0) {
    angle = 180 - angle;
    updateBall();
  } else if (ball.y > theCanvas.height || ball.y < 0) {
    angle = 360 - angle;
    updateBall();
  }
  function updateBall() {
    radians = angle * Math.PI / 180;
    units = Math.cos(radians) * speed;
    yunits = Math.sin(radians) * speed;
    var speed = 5;
    var pi = (1.0/360)*20;
    var angle = 35;
    var radians = 0;
    var units = 0;
    var yunits = 0;
    var ball.x = (xpt-x, ypt-y);
    updateBall();
    theCanvas.document.getElementById("canvasOne");
    context = theCanvas.getContext("2d");
    setInterval(drawScreen, 33);
  }
}
