/**
 * This file is part of Shuup.
 *
 * Copyright (c) 2012-2016, Shoop Ltd. All rights reserved.
 *
 * This source code is licensed under the AGPLv3 license found in the
 * LICENSE file in the root directory of this source tree.
 */
/**
 * Support for media browsing widgets.
 * Currently opens a real, actual, true-to-1998
 * popup window (just like the Django admin, mind)
 * but could just as well use an <iframe> modal.
 */

window.BrowseAPI = (function() {
    const browseData = {};

    window.addEventListener("message", function (event) {
        const data = event.data;
        if (!data.pick) {
            return;
        }
        const info = browseData[data.pick.id];
        if (!info) {
            return;
        }
        info.popup.close();
        const obj = data.pick.object;
        if (!obj) {
            return;
        }
        if (_.isFunction(info.onSelect)) {
            info.onSelect.call(this, obj);
        }
        delete browseData[data.pick.id];
    }, false);

    /**
     * Open a browsing window with the given options.
     *
     * Currently supported options are:
     * * `kind`: kind string (e.g. "product")
     * * `filter`: filter string (kind-dependent)
     * * `onSelect`: a function invoked when an object is selected
     * @return {Object}
     */
    function openBrowseWindow(options) {
        var filter = options.filter;
        const kind = options.kind;
        const browserUrl = window.ShuupAdminConfig.browserUrls[kind];
        if (!browserUrl) {
            throw new Error(gettext("No browser URL for kind:") + " " + kind);
        }
        if(typeof filter !== "string") {
            filter = JSON.stringify(filter);
        }
        const id = "m-" + (+new Date);
        const qs = _.compact([
            "popup=1",
            "pick=" + id,
            (filter ? "filter=" + filter : null)
        ]).join("&");
        const popup = window.open(
            browserUrl + (browserUrl.indexOf("?") > -1 ? "&" : "?") + qs,
            "browser_popup_" + id,
            "resizable,menubar=no,location=no,scrollbars=yes"
        );
        return browseData[id] = _.extend(
            {popup, $container: null, onSelect: null},
            options
        );
    }

    return {
        openBrowseWindow
    };
}());

$(function() {
    $(document).on("click", ".browse-widget .browse-btn", function() {
        const $container = $(this).closest(".browse-widget");
        if (!$container.length) {
            return;
        }
        const kind = $container.data("browse-kind");
        const filter = $container.data("filter");
        try {
            return window.BrowseAPI.openBrowseWindow({kind, filter, onSelect: (obj) => {
                $container.find("input[type=hidden]").val(obj.id);
                const $text = $container.find(".browse-text");
                $text.text(obj.text);
                $text.prop("href", obj.url || "#");
            }});
        } catch(e) {
            alert(e);
            return false;
        }
    });

    $(document).on("click", ".browse-widget .clear-btn", function() {
        const $container = $(this).closest(".browse-widget");
        if (!$container.length) {
            return;
        }
        const emptyText = $container.data("empty-text") || "";
        $container.find("input").val("");
        const $text = $container.find(".browse-text");
        $text.text(emptyText);
        $text.prop("href", "#");
    });

    $(document).on("click", ".browse-widget .browse-text", function(event) {
        const href = $(this).prop("href");
        if (/#$/.test(href)) {  // Looks empty, so prevent clicks
            event.preventDefault();
            return false;
        }
    });

    $(document).on("click", ".browse-widget .duplicate-btn", function() {
        const $container = $(this).closest(".browse-widget");
        if (!$container.length) {
            return;
        }
        const $skuInput = $container.find("input.sku-input");
        const sku = $skuInput.val();
        const nameSuffix = $skuInput.data("suffix");
        const parentId = $skuInput.data("parentId");
        if (!sku){
            window.Messages.enqueue({text: gettext("Unique SKU required to duplicate product.")});
            return;
        }
        $.ajax({
            type: "POST",
            url: window.ShuupAdminConfig.browserUrls.duplicateProduct,
            data: {
                "sku": sku,
                "id": parentId,
                "name_suffix": nameSuffix,
                "csrfmiddlewaretoken": window.ShuupAdminConfig.csrf,
            },
            success: function(data){
                if (data.error) {
                    window.Messages.enqueue({text: data.error});
                }
                else {
                    $skuInput.val('');
                    $container.find("input[type=hidden]").val(data.id);
                    const $text = $container.find(".browse-text");
                    $text.text(data.text);
                    $text.prop("href", data.url || "#");
                }
            },
            error: function(){
                window.Messages.enqueue({text: gettext("There was an error duplicating the product.")});
            },
        });
    });
});
