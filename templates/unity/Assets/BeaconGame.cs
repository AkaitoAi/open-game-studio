using UnityEngine;

public sealed class BeaconGame : MonoBehaviour
{
    private static readonly Vector3 Start = new Vector3(-5, .5f, 2);
    private static readonly Vector3 CoreStart = new Vector3(-3, .35f, -2);

    private Transform robot;
    private Transform core;
    private Transform relay;
    private Renderer relayRenderer;
    private int phase;

    private void Awake()
    {
        Initialize();
    }

    public void Initialize()
    {
        if (robot != null) return;

        MakeBox("Ground", new Vector3(0, -.3f, 0), new Vector3(16, .5f, 12), new Color(.25f, .35f, .46f));
        robot = MakeBox("Robot", Start, new Vector3(.65f, 1, .65f), Color.cyan);
        core = MakeBox("Power Core", CoreStart, Vector3.one * .65f, new Color(1, .78f, .3f));
        relay = MakeBox("Relay", new Vector3(4, .8f, -2), new Vector3(1.3f, 1.6f, 1.3f), Color.gray);
        relayRenderer = relay.GetComponent<Renderer>();

        var camera = new GameObject("Camera").AddComponent<Camera>();
        camera.transform.position = new Vector3(0, 11, -11);
        camera.transform.LookAt(Vector3.zero);
        camera.clearFlags = CameraClearFlags.SolidColor;
        camera.backgroundColor = new Color(.13f, .19f, .28f);

        var light = new GameObject("Sun").AddComponent<Light>();
        light.type = LightType.Directional;
        light.transform.rotation = Quaternion.Euler(55, -25, 0);
    }

    private Transform MakeBox(string label, Vector3 position, Vector3 size, Color color)
    {
        var box = GameObject.CreatePrimitive(PrimitiveType.Cube);
        box.name = label;
        box.transform.SetParent(transform);
        box.transform.position = position;
        box.transform.localScale = size;
        box.GetComponent<Renderer>().material.color = color;
        return box.transform;
    }

    private void Update()
    {
        float x = (Input.GetKey(KeyCode.RightArrow) ? 1 : 0) - (Input.GetKey(KeyCode.LeftArrow) ? 1 : 0);
        float z = (Input.GetKey(KeyCode.UpArrow) ? 1 : 0) - (Input.GetKey(KeyCode.DownArrow) ? 1 : 0);
        var position = robot.position + Vector3.ClampMagnitude(new Vector3(x, 0, z), 1) * (Time.deltaTime * 5);
        robot.position = new Vector3(Mathf.Clamp(position.x, -7, 7), .5f, Mathf.Clamp(position.z, -5, 5));
        if (phase == 1) core.position = robot.position + Vector3.up * .75f;
        if (Input.GetKeyDown(KeyCode.Return)) Interact();
        if (Input.GetKeyDown(KeyCode.R)) ResetRound();
    }

    private void Interact()
    {
        if (phase == 0 && Vector3.Distance(robot.position, core.position) < 1.5f)
        {
            phase = 1;
        }
        else if (phase == 1 && Vector3.Distance(robot.position, relay.position) < 1.8f)
        {
            phase = 2;
            core.position = relay.position + Vector3.up;
            relayRenderer.material.color = Color.green;
        }
    }

    private void ResetRound()
    {
        phase = 0;
        robot.position = Start;
        core.position = CoreStart;
        relayRenderer.material.color = Color.gray;
    }

    private void OnGUI()
    {
        string objective = phase == 0 ? "Find the amber core." :
            phase == 1 ? "Bring the core to the relay." : "Beacon restored!";
        GUI.Label(new Rect(20, 20, 480, 90),
            "BEACON RELAY\n" + objective + "\nArrows: move   Enter: interact   R: restart");
    }

    public bool CheckScenario()
    {
        Initialize();
        Interact();
        bool ok = phase == 0;
        robot.position = core.position;
        Interact();
        ok = ok && phase == 1;
        robot.position = relay.position;
        Interact();
        ok = ok && phase == 2;
        ResetRound();
        return ok && phase == 0 && core.position == CoreStart;
    }
}
