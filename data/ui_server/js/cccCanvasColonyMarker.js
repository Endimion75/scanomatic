function Blob(x, y, r, fill) {
    this.x = x || 0;
    this.y = y || 0;
    this.r = r || 1;
    this.fill = fill || '#AAAAAA';
}

function Shape(x, y, w, h, fill) {
    this.x = x || 0;
    this.y = y || 0;
    this.w = w || 1;
    this.h = h || 1;
    this.fill = fill || '#AAAAAA';
}

Blob.prototype.draw = function(ctx) {
    ctx.fillStyle = this.fill;
    ctx.beginPath();
    ctx.arc(this.x, this.y, this.r, 0, 2 * Math.PI, false);
    ctx.fill();
}

Blob.prototype.contains = function(mx, my) {
    var distancesquared = (mx - this.x) * (mx - this.x) + (my - this.y) * (my - this.y);
    return distancesquared <= Math.pow(this.r, 2);
}

Shape.prototype.draw = function (ctx) {
    ctx.fillStyle = this.fill;
    ctx.fillRect(this.x, this.y, this.w, this.h);
}

Shape.prototype.contains = function (mx, my) {
    return (this.x <= mx) && (this.x + this.w >= mx) &&
        (this.y <= my) && (this.y + this.h >= my);
}

function CanvasState(canvas) {
    this.canvas = canvas;
    this.width = canvas.width;
    this.height = canvas.height;
    this.ctx = canvas.getContext('2d');
    var stylePaddingLeft;
    var stylePaddingTop;
    var styleBorderLeft;
    var styleBorderTop;
    if (document.defaultView && document.defaultView.getComputedStyle) {
        this.stylePaddingLeft = getComputedCanvasStyleInt('paddingLeft');
        this.stylePaddingTop = getComputedCanvasStyleInt('paddingTop');
        this.styleBorderLeft = getComputedCanvasStyleInt('borderLeftWidth');
        this.styleBorderTop = getComputedCanvasStyleInt('borderTopWidth');
    }
    var html = document.body.parentNode;
    this.htmlTop = html.offsetTop;
    this.htmlLeft = html.offsetLeft;

    this.valid = false; 
    this.shapes = [];
    this.dragging = false; 
    this.selection = null;
    this.drawing = false;
    this.dragoffx = 0; 
    this.dragoffy = 0;
  
    var myState = this;

    canvas.addEventListener('selectstart', mySelectStart, false);
    canvas.addEventListener('mousedown', myMousedown, true);
    canvas.addEventListener('mousemove', myMouseMove, true);
    canvas.addEventListener('mouseup', myMouseUp, true);
    canvas.addEventListener('dblclick', myDblClick, true);
    
    this.selectionColorBlob = '#FF0000';
    this.selectionColorShape = '#808080';
    this.selectionWidth = 2;  
    this.interval = 30;
    setInterval(function () { myState.draw(); }, myState.interval);
    function mySelectStart(e) { e.preventDefault(); return false; };

    function myMousedown(e) {
        var mouse = myState.getMouse(e);
        var mx = mouse.x;
        var my = mouse.y;
        var shapes = myState.shapes;
        var l = shapes.length;
        for (var i = l - 1; i >= 0; i--) {
            if (shapes[i].contains(mx, my)) {
                var mySel = shapes[i];
                myState.dragoffx = mx - mySel.x;
                myState.dragoffy = my - mySel.y;
                myState.dragging = true;
                myState.selection = mySel;
                myState.valid = false;
                return;
            }
        }
        // havent returned means we have failed to select anything.
        // If there was an object selected, we deselect it
        if (myState.selection) {
            myState.selection = null;
            myState.valid = false; // Need to clear the old selection border
        }
    };

    function myMouseMove(e) {
        var mouse = myState.getMouse(e);
        if (myState.dragging) {
            myState.selection.x = mouse.x - myState.dragoffx;
            myState.selection.y = mouse.y - myState.dragoffy;
            myState.valid = false; // Something's dragging so we must redraw
        } else if (myState.drawing) {
            myState.selection.w = mouse.x - myState.dragoffx;
            myState.selection.h = mouse.y - myState.dragoffy;
            myState.valid = false; // Something's dragging so we must redraw
        }
    };

    function myMouseUp(e) {
        //recreated shapes with negative w/h so selection works (rework x,y so it always upper left)
        if (myState.drawing) {
            var shape = myState.shapes[myState.shapes.length - 1];
            if (shape.w < 0) {
                shape.x = shape.x + shape.w;
                shape.w = shape.w * -1;
            }
            if (shape.h < 0) {
                shape.y = shape.y + shape.h;
                shape.h = shape.h * -1;
            }
        }
        myState.valid = false;
        myState.dragging = false;
        myState.drawing = false;

    };

    function myDblClick(e) {
        var mouse = myState.getMouse(e);
        var mx = mouse.x;
        var my = mouse.y;
        var shape = new Shape(mouse.x, mouse.y, 1, 1, 'rgba(128,128,128,.6)');
        myState.shapes.push(shape);
        var mySel = shape;
        myState.dragoffx = mx;
        myState.dragoffy = my;
        myState.drawing = true;
        myState.selection = mySel;
        myState.valid = false;
    };

    function getComputedCanvasStyleInt(attribute) {
        var value = parseInt(document.defaultView.getComputedStyle(canvas, null)[attribute], 10) || 0;
        return value;
    }
}

CanvasState.prototype.disposeEventListeners = function () {
    this.canvas.removeEventListener('selectstart', this.mySelectStart, false);
    this.canvas.removeEventListener('mousedown', this.myMousedown, true);
    this.canvas.removeEventListener('mousemove', this.myMouseMove, true);
    this.canvas.removeEventListener('mouseup', this.myMouseUp, true);
    this.canvas.removeEventListener('dblclick', this.myDblClick, true);
}

CanvasState.prototype.addShape = function(shape) {
    this.shapes.push(shape);
    this.valid = false;
}

CanvasState.prototype.removeSelectedShape = function () {
    var mySel = this.selection;
    if (mySel instanceof Blob)
        return;

    var shapes = this.shapes;
    var l = shapes.length;
    for (var i = 0; i < l; i++) {
        var shape = shapes[i];
        if (shape === mySel) {
            shapes.splice(i, 1);
            break;
        }
    }
    this.selection = null;
    this.valid = false;
}

CanvasState.prototype.unSelect = function () {
    this.selection = null;
    this.valid = false;
}

CanvasState.prototype.clear = function() {
    this.ctx.clearRect(0, 0, this.width, this.height);
}

CanvasState.prototype.reset = function () {
    this.ctx.clearRect(0, 0, this.width, this.height);
    this.shapes = [];
    //this.myState = null;
    this.selection = null;
    this.valid = false;
    this.drawing = false;
}

CanvasState.prototype.draw = function() {
    if (!this.valid) {
        var ctx = this.ctx;
        var shapes = this.shapes;
        this.clear();

        var l = shapes.length;
        for (var i = 0; i < l; i++) {
            var shape = shapes[i];
            if (shape.x > this.width || shape.y > this.height ||
                shape.x + shape.w < 0 || shape.y + shape.h < 0) continue;
            shapes[i].draw(ctx);
        }
    
        if (this.selection != null) {
            ctx.lineWidth = this.selectionWidth;
            var mySel = this.selection;
            if (mySel instanceof Shape) {
                ctx.strokeStyle = this.selectionColorShape;
                ctx.strokeRect(mySel.x, mySel.y, mySel.w, mySel.h);
            }
            if (mySel instanceof Blob) {
                ctx.strokeStyle = this.selectionColorBlob;
                ctx.beginPath();
                ctx.arc(mySel.x, mySel.y, mySel.r, 0, 2 * Math.PI, false);
                ctx.stroke();
            }
        }
        this.valid = true;
    }
}

CanvasState.prototype.getMouse = function(e) {
    var element = this.canvas;
    var offsetX = 0;
    var offsetY = 0;
    if (element.offsetParent !== undefined) {
        do {
            offsetX += element.offsetLeft;
            offsetY += element.offsetTop;
        } while ((element = element.offsetParent));
    }

    offsetX += this.stylePaddingLeft + this.styleBorderLeft + this.htmlLeft;
    offsetY += this.stylePaddingTop + this.styleBorderTop + this.htmlTop;

    var mx = e.pageX - offsetX;
    var my = e.pageY - offsetY;
  
    return {x: mx, y: my};
}

