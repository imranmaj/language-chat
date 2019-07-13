$(function() { // on document load
    const LOAD_MESSAGES_COUNT = 20;
    const MESSAGE_TAG = "p";
    const FOCUS_IN_MESSAGE = $("#messageBox").attr("placeholder");
    const FOCUS_OUT_MESSAGE = "Press any key to start typing";

    var socket = io();
    $.fn.isInViewport = function () { // check whether element is in viewport
        var elementTop = $(this).offset().top;
        var elementBottom = elementTop + $(this).outerHeight();
        var viewportTop = $(window).scrollTop();
        var viewportBottom = viewportTop + $(window).height();

        return elementBottom > viewportTop && elementTop < viewportBottom;
    };

    socket.on( // receive a message that was just sent
        "receive-new-message",
        function (message) {
            $("#messages").append(makeMessage(message));
            scrollDown();
        }
    );

    socket.on( // receive a message from history
        "receive-previous-message",
        function(message) {
            $("#messages").prepend(makeMessage(message));
            if (message.scroll) {
                /* Trigger a scroll action if the user dragged the scrollbar to the top
                so messages continue to load */
                $(window).trigger("scroll");
            }
        }
    );

    $(window).scroll(function() { // load new messages
        if ($(window).scrollTop() === 0) { // at the top of the page
            socket.emit("load-previous-message", {scroll: true});
        } else if ($(MESSAGE_TAG).filter(`:lt(${LOAD_MESSAGES_COUNT})`).is(
            function(index, element) {
                return $(element).isInViewport();
            }
        )) { // any of the first 20 loaded messages are on the screen
            socket.emit("load-previous-message", {scroll: false});
        }
    })

    $("form").submit(function (e) { // send message
        e.preventDefault();
        if (( // non-empty message
            $.trim(
                $("#messageBox").val()
            )
        ) != "") {
            socket.emit("send-message", $("#messageBox").val());
        }
        $("#messageBox").val("");
        focusMessageBox();
        return false;
    });

    $(window).keypress(function() { // highlight text box when user starts typing
        focusMessageBox();
    })

    $("#messageBox").focus(function() { // select text box
        $(this).attr("placeholder", FOCUS_IN_MESSAGE);
    })

    $("#messageBox").blur(function() { // de-select text box
        $(this).attr("placeholder", FOCUS_OUT_MESSAGE);
    })

    function scrollDown() { // scroll to bottom of page
        $("html, body").scrollTop($(document).height() - $(window).height());
    }

    function focusMessageBox() {
        $("#messageBox").focus();
    }

    function makeMessage(message) { // create dom elements from message
        return $(`<${MESSAGE_TAG}>`).append(
            $("<b>").text(`${message.username} (${message.timestamp}): `)
        ).append(
            message.content
        );
    }

    // when page is loaded
    socket.emit("connect");
    scrollDown();
    focusMessageBox();
});
