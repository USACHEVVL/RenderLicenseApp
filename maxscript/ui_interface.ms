macroScript RenderNotifySetup
category:"RenderLicenseApp"
tooltip:"Render Notifier"
buttontext:"Notifier"
(
    renderLicense_onRenderStart = undefined
    renderLicense_onRenderEnd = undefined
    getRenderViewName = undefined

    rollout RenderNotifyRollout "Render License Notifier" width:300
    (
		edittext licenseInput "License Key:" width:280 align:#center limitText:36
        button checkBtn "License check" width:280 align:#center
        label userIdLabel "" width:280 align:#center
        checkbox notifyStart "Notify on render start" width:280 align:#center indent:-15
        label statusLabel "Checking license..." width:280 align:#center
        button renewBtn "Renew license" width:280 align:#center visible:false

        fn checkLicense key =
        (
            local url = "http://127.0.0.1:8000/api/check_license?license_key=" + key
            try
            (
                local wc = dotNetObject "System.Net.WebClient"
                wc.Encoding = (dotNetClass "System.Text.Encoding").UTF8
                local raw = wc.DownloadString url

                try (
                    local jsonPath = getFilenamePath (getSourceFileName()) + "Newtonsoft.Json.dll"
                    if doesFileExist jsonPath then (
                        dotNet.loadAssembly jsonPath
                    ) else (
                        messageBox "❌ Newtonsoft.Json.dll not found" title:"RenderLicenseApp"
                        userIdLabel.text = ""
                        return undefined
                    )
                ) catch (
                    messageBox "❌ Ошибка загрузки Newtonsoft.Json.dll" title:"RenderLicenseApp"
                    userIdLabel.text = ""
                    return undefined
                )

                print raw

                local json = (dotNetClass "Newtonsoft.Json.JsonConvert").DeserializeObject raw
if json != undefined and json.ContainsKey "status" then (
    local statusToken = json.Item["status"]
    local status = statusToken.ToString()
    format "Parsed status: %
" status

    case status of (
    "active": (
        messageBox "✅ License active"
        if (json.ContainsKey "user_id") and (json.ContainsKey "days_left") do (
            local userId = json.Item["user_id"]
            local daysLeft = json.Item["days_left"]
                        userIdLabel.text = "ID: " + userId.ToString() + " (" + daysLeft.ToString() + " days left)"
        )
        statusLabel.text = "✅ License is active"
        renewBtn.visible = false
    )
    "not_found": (
        messageBox "❌ License not found"
        userIdLabel.text = ""
        statusLabel.text = "❌ License not found"
        renewBtn.visible = false
    )
    "expired": (
        messageBox "⏳ License expired"
        userIdLabel.text = ""
        statusLabel.text = "⏳ License expired"
        renewBtn.visible = true
    )
    default: (
        messageBox "❌ Invalid server response"
        userIdLabel.text = ""
        statusLabel.text = "❌ Invalid response"
        renewBtn.visible = false
    )
)

) else (
    messageBox "❌ Invalid server response"
    userIdLabel.text = ""
    renewBtn.visible = false
)
            )
            catch (
                try (
                    local ex = getCurrentException()
                    local exType = "Unknown"
                    try (
                        if ex != undefined then (
                            local dotType = ex.GetType()
                            exType = dotType.Name
                        )
                    ) catch ()

                    if exType == "System.Net.WebException" then
                        messageBox "🌐❌ No connection to server"
                    else (
                        format "Exception: %\n" ex
                        messageBox ("Unknown error:\n" + ex.ToString())
                        statusLabel.text = "Error: " + ex.Message
                    )
                ) catch (
                    messageBox "❌ Critical error during license check"
                )
                renewBtn.visible = false
            )
        )

        on licenseInput entered val do
        (
            local iniPath = getDir #userScripts + "\\render_license_config.ini"
            setINISetting iniPath "RenderLicense" "license_key" val
        )

        on notifyStart changed state do
        (
            local iniPath = getDir #userScripts + "\\render_license_config.ini"
            setINISetting iniPath "RenderLicense" "notify_start" (if state then "true" else "false")
        )

        fn loadSettings =
        (
            local iniPath = getDir #userScripts + "\\render_license_config.ini"
            licenseInput.text = getINISetting iniPath "RenderLicense" "license_key"
            notifyStart.checked = (getINISetting iniPath "RenderLicense" "notify_start") == "true"
            if licenseInput.text != "" then (
                checkLicense licenseInput.text
            )
        )

        on RenderNotifyRollout open do
        (
            loadSettings()

            callbacks.removeScripts id:#renderLicenseStart
            callbacks.removeScripts id:#renderLicenseEnd

            callbacks.addScript #preRender "if (::renderLicense_onRenderStart != undefined) then ::renderLicense_onRenderStart()" id:#renderLicenseStart
            callbacks.addScript #postRender "if (::renderLicense_onRenderEnd != undefined) then ::renderLicense_onRenderEnd()" id:#renderLicenseEnd
        )

        on checkBtn pressed do (
            checkLicense licenseInput.text
        )
        on renewBtn pressed do shellLaunch "https://t.me/Ano3D_bot?start=команда" ""
    )

    fn renderLicense_escape str =
    (
        local res = substituteString str "\\" "\\\\"
        res = substituteString res "\"" "\\\""
        res = substituteString res "\n" "\\n"
        res
    )

    fn licenseIsActive key =
    (
        if key == "" then (
            RenderNotifyRollout.statusLabel.text = "⚠️ License missing"
            return false
        )

        local url = "http://127.0.0.1:8000/api/check_license?license_key=" + key
        try (
            try (
                dotNet.loadAssembly (getFilenamePath (getSourceFileName()) + "Newtonsoft.Json.dll")
            ) catch ()

            local wc = dotNetObject "System.Net.WebClient"
            wc.Encoding = (dotNetClass "System.Text.Encoding").UTF8
            local raw = wc.DownloadString url

            local json = (dotNetClass "Newtonsoft.Json.JsonConvert").DeserializeObject raw
            if json != undefined and json.ContainsKey "status" then (
                local status = json.Item["status"].ToString()
                case status of (
                    "active": (
                        if (json.ContainsKey "user_id") and (json.ContainsKey "days_left") do (
                            local userId = json.Item["user_id"]
                            local daysLeft = json.Item["days_left"]
                            RenderNotifyRollout.userIdLabel.text = "ID: " + userId.ToString() + " (" + daysLeft.ToString() + " days left)"
                        )
                        RenderNotifyRollout.statusLabel.text = "✅ License is active"
                        RenderNotifyRollout.renewBtn.visible = false
                        return true
                    )
                    "expired": (
                        RenderNotifyRollout.statusLabel.text = "⏳ License expired"
                        RenderNotifyRollout.renewBtn.visible = true
                    )
                    "not_found": (
                        RenderNotifyRollout.statusLabel.text = "❌ License not found"
                        RenderNotifyRollout.renewBtn.visible = false
                    )
                    default: (
                        RenderNotifyRollout.statusLabel.text = "❌ Invalid response"
                        RenderNotifyRollout.renewBtn.visible = false
                    )
                )
            ) else (
                RenderNotifyRollout.statusLabel.text = "❌ Invalid response"
                RenderNotifyRollout.renewBtn.visible = false
            )
        ) catch (
            RenderNotifyRollout.statusLabel.text = "⚠️ License check failed"
            RenderNotifyRollout.renewBtn.visible = false
        )
        false
    )

    fn renderLicense_sendLog license logText =
    (
        local escapedLog = renderLicense_escape logText
        local url = "http://127.0.0.1:8000/api/render_notify"
        local json = "{\"license_key\":\"" + license + "\",\"log\":\"" + escapedLog + "\"}"

        try (
            local wc = dotNetObject "System.Net.WebClient"
            wc.Headers.Add "Content-Type" "application/json; charset=utf-8"
            wc.Encoding = (dotNetClass "System.Text.Encoding").UTF8
            wc.UploadData url "POST" ((dotNetClass "System.Text.Encoding").UTF8.GetBytes json)
        ) catch (
            format "RenderLicense: failed to send log to server: %\n" (getCurrentException())
        )
    )

    fn getRenderViewName =
    (
        local cam = undefined
        try (cam = renderCamera) catch (cam = undefined)
        if cam == undefined do try (cam = viewport.getCamera()) catch (cam = undefined)

        if cam != undefined then
            try (cam.name) catch ("Camera")
        else (
            local vt = viewport.getType()
            case vt of
            (
                #view_persp_user:  "Perspective"
                #view_ortho_user:  "Orthographic"
                #view_iso_user:    "Orthographic"
                #view_top:         "Top"
                #view_bottom:      "Bottom"
                #view_front:       "Front"
                #view_back:        "Back"
                #view_left:        "Left"
                #view_right:       "Right"
                default:           (vt as string)
            )
        )
    )

    fn renderLicense_onRenderStart =
    (
        local iniPath = getDir #userScripts + "\\render_license_config.ini"
        local notifyStart = getINISetting iniPath "RenderLicense" "notify_start"
        local license = getINISetting iniPath "RenderLicense" "license_key"

        if notifyStart == "true" and (licenseIsActive license) then (
            local sceneName = if maxFileName != "" then maxFileName else "Untitled"
            local cameraName = getRenderViewName()

            local now = (dotNetClass "System.DateTime").Now
            local timeStr = now.ToString "HH:mm:ss"
            local dateStr = now.ToString "dd.MM.yyyy"

            local logText =
                "🎬 Render started\n" +
                "⏰ Time: " + timeStr + "\n" +
                "🗕 Date: " + dateStr + "\n" +
                "🗜 Scene: " + sceneName + "\n" +
                "📷 View: " + cameraName

            renderLicense_sendLog license logText
        )
    )

    fn renderLicense_onRenderEnd =
    (
        local iniPath = getDir #userScripts + "\\render_license_config.ini"
        local license = getINISetting iniPath "RenderLicense" "license_key"

        if licenseIsActive license then (
            local sceneName = if maxFileName != "" then maxFileName else "Untitled"
            local cameraName = getRenderViewName()

            local now = (dotNetClass "System.DateTime").Now
            local timeStr = now.ToString "HH:mm:ss"
            local dateStr = now.ToString "dd.MM.yyyy"

            local logText =
                "🎬 Render finished\n" +
                "⏰ Time: " + timeStr + "\n" +
                "🗕 Date: " + dateStr + "\n" +
                "🗜 Scene: " + sceneName + "\n" +
                "📷 View: " + cameraName

            renderLicense_sendLog license logText
        )
    )

    createDialog RenderNotifyRollout
)
