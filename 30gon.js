function draw() {
    var canvas = document.getElementById('30gon');
    if (canvas.getContext){
	var ctx = canvas.getContext('2d');

	var path=new Path2D();
	var radius=200;
	var margin=20;
	var verts = 30;

	var center_x = radius + margin;
	var center_y = radius + margin;

	var circum = Math.PI*2

	// Outer circle
	path.arc(center_x, center_y, radius, 0, circum, true);
	ctx.lineWidth = 3;
	ctx.stroke(path);

	path=new Path2D;
	for (i = 0; i < verts; i++) {
	    angle = (circum / verts) * i;
	    edge_x = center_x + radius * Math.sin(angle);
	    edge_y = center_y + radius * Math.cos(angle);
	    for (j = i + 1; j < verts; j++) {
		anglej = (circum / verts) * j;
		edgej_x = center_x + radius * Math.sin(anglej);
		edgej_y = center_y + radius * Math.cos(anglej);
		path.moveTo(edge_x, edge_y);
		path.lineTo(edgej_x, edgej_y);
	    }
	}
	ctx.lineWidth = 2;
	ctx.stroke(path);
    }
}
