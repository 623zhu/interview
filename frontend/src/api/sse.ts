export async function readSseStream(
  response: Response,
  onEvent: (event: string, data: unknown) => void,
): Promise<void> {
  if (!response.body) {
    throw new Error('empty stream')
  }
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    buffer = buffer.replace(/\r\n/g, '\n')
    let separator = buffer.indexOf('\n\n')
    while (separator >= 0) {
      const block = buffer.slice(0, separator)
      buffer = buffer.slice(separator + 2)
      let event = 'message'
      const dataLines: string[] = []
      for (const line of block.split('\n')) {
        if (line.startsWith('event:')) {
          event = line.slice(6).trim()
        } else if (line.startsWith('data:')) {
          dataLines.push(line.slice(5).trimStart())
        }
      }
      if (dataLines.length) {
        onEvent(event, JSON.parse(dataLines.join('\n')))
      }
      separator = buffer.indexOf('\n\n')
    }
  }
}
