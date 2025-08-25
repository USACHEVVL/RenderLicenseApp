macroScript RenderNotifySetup
category:"RenderLicenseApp"
tooltip:"Render Notifier"
buttontext:"Notifier"
(
    global renderLicense_onRenderStart
    global renderLicense_onRenderEnd
    global getRenderViewName

    rollout RenderNotifyRollout "Render License Notifier" width:300
    (
        edittext licenseInput "License Key:" width:280
        button checkBtn "License check" width:280
        label userIdLabel "" width:280
        checkbox notifyStart "Notify on render start"
        label statusLabel "Checking license..." width:280

        fn checkLicense key =
        (
            local url = "http://127.0.0.1:8000/api/check_license?license_key=" + key
            try
            (
                local wc = dotNetObject "System.Net.WebClient"
                wc.Encoding = (dotNetClass "System.Text.Encoding").UTF8
                local raw = wc.DownloadString url

                local json = undefined
                try json = parseJSON raw catch()
                if json != undefined and isProperty json #status then (
                    case json.status of
                    (
                        "active": (
                            messageBox "✅ License active"
                            userIdLabel.text = "ID: " + json.user_id
                        )
                        "not_found": (
                            messageBox "❌ License not found"
                            userIdLabel.text = ""
                        )
                        "expired": (
                            messageBox "⏳ License expired"
                            userIdLabel.text = ""
                        )
                        default:
                        (
                            messageBox "❌ Invalid server response"
                            userIdLabel.text = ""
                        )
                    )
                )
                else (
                    messageBox "❌ Invalid server response"
                    userIdLabel.text = ""
                )
            )
            catch
            (
                messageBox "🌐❌ No connection to server"
                userIdLabel.text = ""
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
        on checkBtn pressed do checkLicense licenseInput.text
    )

     fn renderLicense_escape str =
    (
        local res = substituteString str "\\" "\\\\"
        res = substituteString res "\"" "\\\""
        res = substituteString res "\n" "\\n"
        res
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

    if license == "" do (
        messageBox "⚠️ License is missing. Logging without key." title:"RenderLicenseApp"
    )

    local sceneName
    if maxFileName != "" then
        sceneName = maxFileName
    else
        sceneName = "Untitled"

    local cameraName = getRenderViewName()

    local now = (dotNetClass "System.DateTime").Now
    local timeStr = now.ToString "HH:mm:ss"
    local dateStr = now.ToString "dd.MM.yyyy"

    local logText =
        "🎬 Render started\n" +
        "⏰ Time: " + timeStr + "\n" +
        "📅 Date: " + dateStr + "\n" +
        "🖼 Scene: " + sceneName + "\n" +
        "📷 View: " + cameraName

    if notifyStart == "true" then (
        -- messageBox logText title:"RenderLicenseApp"
        renderLicense_sendLog license logText
    )
)


    fn renderLicense_onRenderEnd =
    (
        local iniPath = getDir #userScripts + "\\render_license_config.ini"
        local license = getINISetting iniPath "RenderLicense" "license_key"
        if license == "" do (
            messageBox "⚠️ License is missing. Logging without key." title:"RenderLicenseApp"
        )

        local sceneName = if maxFileName != "" then maxFileName else "Untitled"
        local cameraName = getRenderViewName()

        local now = (dotNetClass "System.DateTime").Now
        local timeStr = now.ToString "HH:mm:ss"
        local dateStr = now.ToString "dd.MM.yyyy"

        local logText =
            "🎬 Render finished\n" +
            "⏰ Time: " + timeStr + "\n" +
            "📅 Date: " + dateStr + "\n" +
            "🖼 Scene: " + sceneName + "\n" +
            "📷 View: " + cameraName

        -- messageBox logText title:"RenderLicenseApp"
        renderLicense_sendLog license logText
    )

    createDialog RenderNotifyRollout
)
