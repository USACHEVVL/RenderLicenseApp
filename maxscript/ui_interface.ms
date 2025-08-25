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
        label statusLabel "Checking license..." width:280
        checkbox notifyStart "Notify on render start"

        fn checkLicense key =
        (
            local url = "http://127.0.0.1:8000/api/check_license?license_key=" + key
            local outputFile = getDir #temp + "\\license_check_result.json"
            local statusFile = getDir #temp + "\\license_check_status.txt"

            local cmd = "curl -s -o \"" + outputFile + "\" -w \"%{http_code}\" \"" + url + "\" > \"" + statusFile + "\""
            shellLaunch "cmd.exe" ("/C " + cmd)

            for i = 1 to 20 while (not (doesFileExist statusFile)) do sleep 0.1
            for i = 1 to 20 while (not (doesFileExist outputFile)) do sleep 0.1

            local httpCode = undefined
            if doesFileExist statusFile then (
                local sf = openFile statusFile
                httpCode = readLine sf
                close sf
                deleteFile statusFile
            )

            if httpCode == "200" then (
                if doesFileExist outputFile then (
                    local f = openFile outputFile
                    local raw = readLine f
                    close f
                    deleteFile outputFile

                    if raw != undefined and raw != "" then (
                        try (
                            local json = parseJSON raw
                            if json != undefined then (
                                if json.valid != undefined then (
                                    if json.valid == true then
                                        statusLabel.text = "✅ License valid"
                                    else
                                        statusLabel.text = "❌ License invalid"
                                ) else if json.status != undefined then (
                                    if json.status == "✅ valid" then
                                        statusLabel.text = "✅ License valid"
                                    else
                                        statusLabel.text = "❌ License invalid"
                                ) else (
                                    statusLabel.text = "❌ Invalid server response"
                                )
                            ) else (
                                statusLabel.text = "❌ Invalid server response"
                            )
                        ) catch (
                            statusLabel.text = "❌ Invalid server response"
                        )
                    ) else (
                        statusLabel.text = "❌ Empty or undefined response"
                    )
                ) else (
                    statusLabel.text = "❌ Output file missing"
                )
            ) else if httpCode == "404" then (
                statusLabel.text = "❌ API endpoint not found"
            ) else if httpCode != undefined then (
                statusLabel.text = "❌ Server error (" + httpCode + ")"
            ) else (
                statusLabel.text = "❌ Server not available"
            )
        )

        on licenseInput entered val do
        (
            statusLabel.text = "Checking..."
            checkLicense val

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
                statusLabel.text = "Checking..."
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
            wc.Headers.Add "Content-Type" "application/json"
            wc.Encoding = (dotNetClass "System.Text.Encoding").UTF8
            wc.UploadString url json
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
    local startTime = localTime as string

    local logText = "🖼 Scene: " + sceneName + "\n" +
                    "📷 View: " + cameraName + "\n" +
                    "🚀 Render start: " + startTime + "\n"

    if notifyStart == "true" then (
        messageBox logText title:"RenderLicenseApp"
        renderLicense_sendLog license logText
    )
)


    fn renderLicense_onRenderEnd =
    (
        local iniPath = getDir #userScripts + "\\render_license_config.ini"
        local notifyStart = getINISetting iniPath "RenderLicense" "notify_start"
        local license = getINISetting iniPath "RenderLicense" "license_key"
        if license == "" do (
            messageBox "⚠️ License is missing. Logging without key." title:"RenderLicenseApp"
        )

        local sceneName = if maxFileName != "" then maxFileName else "Untitled"
        local cameraName = getRenderViewName()
        local endTime = localTime as string

        local logText = "🖼 Scene: " + sceneName + "\n" +
                        "📷 View: " + cameraName + "\n" +
                        "⏰ Render finished: " + endTime + "\n"

        if notifyStart == "true" then (
            messageBox logText title:"RenderLicenseApp"
            renderLicense_sendLog license logText
        )
    )

    createDialog RenderNotifyRollout
)
