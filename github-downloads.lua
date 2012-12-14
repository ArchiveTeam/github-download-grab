html_entity_convert = function(entity)
    if entity == "amp" then
        return "&"
    elseif entity == "lt" then
        return "<"
    elseif entity == "gt" then
        return ">"
    elseif entity == "quot" then
        return "\""
    end
    return "&"..entity..";"
end

html_entities_decode = function(url)
    return string.gsub(url, "&([a-z]+);", html_entity_convert)
end

read_file = function(file)
  if file then
    local f = io.open(file)
    local data = f:read("*all")
    f:close()
    return data
  else
    return ""
  end
end

local dl_counter = 0

wget.callbacks.get_urls = function(file, url, is_css, iri)
  local urls = {}

  if string.match(url, "/downloads$") then
    local html = read_file(file)

    for dl_path in string.gmatch(html, "<a href=\"(/downloads/[^\"]+)\">") do
      table.insert(urls, { url=("https://github.com"..html_entities_decode(dl_path)) })
    end

    dl_count = #urls
    print("- Discovering downloads: "..dl_count.." found.")
  end

  if string.match(url, "http://cloud.github.com/downloads/") then
    dl_counter = dl_counter + 1
    print("- Download "..dl_counter.." of "..dl_count.." complete.")
  end

  return urls
end

wget.callbacks.httploop_result = function(url, err, http_stat)
  if http_stat.statcode == 502 or http_stat.statcode == 504 then
    -- gateway error, retry
    os.execute("sleep 10")
    return wget.actions.CONTINUE
  else
    return wget.actions.NOTHING
  end
end

