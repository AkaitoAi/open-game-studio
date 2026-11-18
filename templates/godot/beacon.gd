extends Node3D

var robot: Node3D
var core: Node3D
var dish: Node3D
var hud: Label
var phase := 0


func _ready() -> void:
	var sky := WorldEnvironment.new()
	sky.environment = Environment.new()
	sky.environment.background_mode = Environment.BG_COLOR
	sky.environment.background_color = Color("#223049")
	sky.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	sky.environment.ambient_light_color = Color.WHITE
	sky.environment.ambient_light_energy = 0.7
	add_child(sky)
	var light := DirectionalLight3D.new()
	light.rotation_degrees = Vector3(-55, -25, 0)
	light.shadow_enabled = true
	add_child(light)
	_box(Vector3(0, -0.3, 0), Vector3(16, 0.5, 12), Color("#415871"))
	robot = _box(Vector3(-5, 0.5, 2), Vector3(0.65, 1, 0.65), Color("#70e8e4"))
	core = _box(Vector3(-3, 0.35, -2), Vector3(0.65, 0.65, 0.65), Color("#fcd075"))
	dish = _box(Vector3(4, 0.8, -2), Vector3(1.3, 1.6, 1.3), Color("#8393b4"))
	var camera := Camera3D.new()
	add_child(camera)
	camera.position = Vector3(0, 11, 11)
	camera.look_at(Vector3.ZERO)
	camera.make_current()
	hud = Label.new()
	hud.position = Vector2(20, 20)
	hud.add_theme_font_size_override("font_size", 20)
	add_child(hud)
	_update_hud()
	if "--studio-smoke" in OS.get_cmdline_user_args():
		_smoke()


func _box(where: Vector3, size: Vector3, color: Color) -> MeshInstance3D:
	var instance := MeshInstance3D.new()
	var mesh := BoxMesh.new()
	mesh.size = size
	instance.mesh = mesh
	var material := StandardMaterial3D.new()
	material.albedo_color = color
	instance.material_override = material
	add_child(instance)
	instance.position = where
	return instance


func _physics_process(delta: float) -> void:
	var direction := Input.get_vector("ui_left", "ui_right", "ui_up", "ui_down")
	robot.position += Vector3(direction.x, 0, direction.y) * delta * 5.0
	robot.position.x = clampf(robot.position.x, -7, 7)
	robot.position.z = clampf(robot.position.z, -5, 5)
	if phase == 1:
		core.position = robot.position + Vector3(0, 0.75, 0)


func _unhandled_key_input(event: InputEvent) -> void:
	if event.is_pressed() and not event.is_echo():
		if event.is_action_pressed("ui_accept"):
			_interact()
		elif event is InputEventKey and event.keycode == KEY_R:
			_reset()


func _interact() -> void:
	if phase == 0 and robot.position.distance_to(core.position) < 1.5:
		phase = 1
	elif phase == 1 and robot.position.distance_to(dish.position) < 1.8:
		phase = 2
		core.position = dish.position + Vector3.UP
		dish.material_override.albedo_color = Color("#77efab")
	_update_hud()


func _reset() -> void:
	phase = 0
	robot.position = Vector3(-5, 0.5, 2)
	core.position = Vector3(-3, 0.35, -2)
	dish.material_override.albedo_color = Color("#8393b4")
	_update_hud()


func _update_hud() -> void:
	var objectives := ["Find the amber core.", "Bring the core to the relay.", "Beacon restored!"]
	hud.text = "BEACON RELAY\n%s\nArrows: move   Enter: interact   R: restart" % objectives[phase]


func _smoke() -> void:
	_interact()
	var ok := phase == 0
	robot.position = core.position
	_interact()
	ok = ok and phase == 1
	robot.position = dish.position
	_interact()
	ok = ok and phase == 2
	_reset()
	ok = ok and phase == 0 and core.position == Vector3(-3, 0.35, -2)
	print("Beacon Relay scenario: ", "PASS" if ok else "FAIL")
	get_tree().quit(0 if ok else 1)
