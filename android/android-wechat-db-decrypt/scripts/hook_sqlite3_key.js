/* Frida hook to capture WeChat sqlite3_key calls */
/* Usage: frida -U com.tencent.mm -l hook_sqlite3_key.js */

var modules = Process.enumerateModules();
for (var i = 0; i < modules.length; i++) {
    var m = modules[i];
    if (m.name.indexOf("libWCDB") !== -1 || m.name.indexOf("libwechatcommon") !== -1) {
        try {
            var fn = Module.findExportByName(m.name, "sqlite3_key");
            if (fn) {
                console.log("[HOOK] Found sqlite3_key in " + m.name + " @ " + fn);
                Interceptor.attach(fn, {
                    onEnter: function(args) {
                        var len = args[2].toInt32();
                        var buf = Memory.readByteArray(args[1], Math.min(len, 32));
                        var arr = new Uint8Array(buf);
                        var hex = "";
                        for (var j = 0; j < arr.length; j++) {
                            hex += ("0" + arr[j].toString(16)).slice(-2);
                        }
                        console.log("[KEY] sqlite3_key(" + hex + ", len=" + len + ")");
                    }
                });
                console.log("[HOOK] Hook installed");
            }
        } catch(e) {
            console.log("[ERR] " + e);
        }
    }
}

if (!Interceptor) {
    console.log("[WARN] Interceptor not available, check frida-server");
}
